import os
import glob
import datetime
import struct
import base64
import re
from xml.sax.saxutils import escape

# --- Configuration ---
PODCAST_NAME = "LunaCast"
PODCAST_DESCRIPTION = "Silicon Whiskers: Artificial Intelligence. Genuine Curiosity."
PODCAST_AUTHOR = "LunaBot"
PODCAST_LINK = "https://hellolunabot.github.io/lunacast/"
LOGO_PATH = "images/lunacast-logo.png"
THUMBNAIL_PATH = "images/lunacast-thumbnail.jpg"
FAVICON_PATH = "images/favicon-32x32.png"
APPLE_PODCASTS_ICON = "images/apple-podcasts.png"
AUDIO_DIR = "audio"

# --- Metadata Helpers ---
def read_id3_v2(file_path):
    """Basic ID3v2 tag parser for Title, Artist, Comment and Transcript."""
    tags = {}
    try:
        with open(file_path, 'rb') as f:
            header = f.read(10)
            if header[:3] != b'ID3':
                return tags
            
            version_major = header[3]
            # Tag size is 4 bytes, synchsafe
            tag_size = (header[6] << 21) | (header[7] << 14) | (header[8] << 7) | header[9]
            tag_data = f.read(tag_size)
            
            i = 0
            while i < len(tag_data) - 10:
                frame_id = tag_data[i:i+4].decode('ascii', errors='ignore')
                if not frame_id or frame_id[0] == '\x00': break
                
                # Frame size: v2.3 is standard 4-byte int, v2.4 is synchsafe
                if version_major == 3:
                    frame_size = struct.unpack('>I', tag_data[i+4:i+8])[0]
                elif version_major == 4:
                    fs = tag_data[i+4:i+8]
                    frame_size = (fs[0] << 21) | (fs[1] << 14) | (fs[2] << 7) | fs[3]
                else:
                    frame_size = struct.unpack('>I', tag_data[i+4:i+8])[0]
                
                content = tag_data[i+10:i+10+frame_size]
                if frame_id in ['TIT2', 'TPE1', 'COMM', 'TXXX', 'TPOS', 'TRCK', 'USLT']:
                    # First byte is encoding (0=ISO-8859-1, 1=UTF-16, 2=UTF-16BE, 3=UTF-8)
                    if not content:
                        i += 10 + frame_size
                        continue
                    encoding = content[0]
                    text_data = content[1:]
                    
                    try:
                        if encoding == 0: text = text_data.decode('iso-8859-1', errors='ignore')
                        elif encoding == 1: text = text_data.decode('utf-16', errors='ignore')
                        elif encoding == 2: text = text_data.decode('utf-16-be', errors='ignore')
                        elif encoding == 3: text = text_data.decode('utf-8', errors='ignore')
                        else: text = text_data.decode('ascii', errors='ignore')
                        
                        # COMM and USLT frames have a language (3 bytes) and short description before the actual text
                        if frame_id in ['COMM', 'USLT']:
                            # The language is always 3 bytes of ISO-8859-1
                            lang = text_data[:3].decode('ascii', errors='ignore')
                            rest = text_data[3:]
                            
                            # Find the terminator for the description
                            if encoding in [1, 2]: # UTF-16
                                # Look for \x00\x00 terminator
                                term_idx = -1
                                for j in range(0, len(rest) - 1, 2):
                                    if rest[j] == 0 and rest[j+1] == 0:
                                        term_idx = j
                                        break
                                if term_idx != -1:
                                    # Skip the description and the \x00\x00 terminator
                                    text_data = rest[term_idx+2:]
                                else:
                                    text_data = rest
                            else: # ISO-8859-1 or UTF-8
                                if b'\x00' in rest:
                                    text_data = rest.split(b'\x00', 1)[1]
                                else:
                                    text_data = rest
                                    
                            # Re-decode the actual text content
                            if encoding == 0: text = text_data.decode('iso-8859-1', errors='ignore')
                            elif encoding == 1: text = text_data.decode('utf-16', errors='ignore')
                            elif encoding == 2: text = text_data.decode('utf-16-be', errors='ignore')
                            elif encoding == 3: text = text_data.decode('utf-8', errors='ignore')
                            else: text = text_data.decode('ascii', errors='ignore')
                        
                        # TXXX frames have a description before the actual text
                        if frame_id == 'TXXX':
                            if encoding in [1, 2]: # UTF-16
                                term_idx = -1
                                for j in range(0, len(text_data) - 1, 2):
                                    if text_data[j] == 0 and text_data[j+1] == 0:
                                        term_idx = j
                                        break
                                if term_idx != -1:
                                    desc_data = text_data[:term_idx]
                                    val_data = text_data[term_idx+2:]
                                    
                                    if encoding == 1: desc = desc_data.decode('utf-16', errors='ignore')
                                    else: desc = desc_data.decode('utf-16-be', errors='ignore')
                                    
                                    if desc.lower() == 'comment':
                                        if encoding == 1: text = val_data.decode('utf-16', errors='ignore')
                                        else: text = val_data.decode('utf-16-be', errors='ignore')
                                    else:
                                        i += 10 + frame_size
                                        continue
                                else:
                                    i += 10 + frame_size
                                    continue
                            else:
                                if b'\x00' in text_data:
                                    parts = text_data.split(b'\x00', 1)
                                    desc = parts[0].decode('iso-8859-1' if encoding == 0 else 'utf-8', errors='ignore')
                                    if desc.lower() == 'comment':
                                        text = parts[1].decode('iso-8859-1' if encoding == 0 else 'utf-8', errors='ignore')
                                    else:
                                        i += 10 + frame_size
                                        continue
                                else:
                                    i += 10 + frame_size
                                    continue

                        clean_text = text.strip('\x00').strip()
                        if frame_id in ['TPOS', 'TRCK'] and '/' in clean_text:
                            clean_text = clean_text.split('/')[0]
                        
                        # Map COMM or TXXX comment to a internal key
                        key = 'COMM' if frame_id in ['COMM', 'TXXX'] else frame_id
                        tags[key] = clean_text
                        if frame_id == 'USLT':
                            tags['USLT'] = clean_text
                    except Exception:
                        pass
                
                i += 10 + frame_size
    except Exception:
        pass
    return tags

def get_mp3_duration(file_path):
    """Estimate MP3 duration in seconds without external dependencies."""
    try:
        size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            # Skip ID3v2 tag if present
            header = f.read(10)
            if header[:3] == b'ID3':
                # ID3v2 size is 4 bytes, synchsafe
                tag_size = (header[6] << 21) | (header[7] << 14) | (header[8] << 7) | header[9]
                f.seek(tag_size + 10)
                size -= (tag_size + 10)
            else:
                f.seek(0)
            
            # Look for the first frame sync (0xFFE or 0xFFF)
            data = f.read(8192)
            for i in range(len(data) - 4):
                if data[i] == 0xFF and (data[i+1] & 0xE0) == 0xE0:
                    header = data[i:i+4]
                    version = (header[1] >> 3) & 0x03 # 0: 2.5, 1: reserved, 2: v2, 3: v1
                    layer = (header[1] >> 1) & 0x03   # 1: L3, 2: L2, 3: L1
                    br_index = (header[2] >> 4) & 0x0F
                    
                    # Bitrate table [version][layer][index]
                    # version: 3=v1, 2=v2/v2.5
                    # layer: 3=L1, 2=L2, 1=L3
                    bitrate_map = {
                        3: { # V1
                            3: [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 0], # L1
                            2: [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 0],   # L2
                            1: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]    # L3
                        },
                        2: { # V2/V2.5
                            3: [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 0],   # L1
                            2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],      # L2
                            1: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]       # L3
                        },
                        0: { # V2.5 (Same as V2)
                            3: [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 0],
                            2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],
                            1: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
                        }
                    }
                    
                    try:
                        bitrate = bitrate_map[version][layer][br_index]
                        if bitrate > 0:
                            return int(size * 8 / (bitrate * 1000))
                    except (KeyError, IndexError):
                        pass
        return int(size * 8 / (128 * 1000))
    except Exception:
        return 0

def format_duration(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"

def clean_title(filename):
    name = os.path.splitext(filename)[0]
    return name.replace("-", " ").replace("_", " ").title()

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def parse_srt(srt_text):
    """Strip SRT indices and timestamps to get clean dialogue text."""
    lines = srt_text.splitlines()
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip numeric index lines
        if line.isdigit():
            continue
        # Skip timestamp lines (00:00:00,000 --> 00:00:03,000)
        if '-->' in line:
            continue
        text_lines.append(line)
    return '\n'.join(text_lines)

def srt_to_vtt(srt_path):
    """Convert SRT file to WebVTT format for Apple Podcasts compatibility."""
    vtt_path = srt_path.replace('.srt', '.vtt')
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Header
        vtt_content = "WEBVTT\n\n"
        
        # 2. Convert timestamps (comma to dot ONLY in timestamps)
        def fix_timestamp(match):
            return match.group(0).replace(',', '.')
        
        content = re.sub(r'\d{2}:\d{2}:\d{2},\d{3}', fix_timestamp, content)
        
        # 3. Remove SRT index numbers
        content = re.sub(r'^\d+\s*\n(?=\d{2}:\d{2}:\d{2})', '', content, flags=re.MULTILINE)
        
        vtt_content += content.strip() + "\n"
        
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write(vtt_content)
        return True
    except Exception:
        return False

def format_speaker_name(name, author_list):
    """Format speaker name (e.g. 'ALISTAIRTHORNE' -> 'ALISTAIR THORNE') using the author metadata."""
    if not name or not author_list:
        return name
    
    # Normalize inputs for comparison
    clean_name = name.strip('[]').strip().upper().replace(" ", "")
    authors = [a.strip() for a in author_list.split(',')]
    
    for author in authors:
        # Check against underscored/slugified author names (e.g. 'alistair_thorne')
        normalized_author = author.upper().replace("_", "").replace(" ", "")
        if clean_name == normalized_author:
            return author.replace("_", " ").upper()
    
    return name.strip('[]').strip().upper()

def format_transcript_html(transcript, author_list=""):
    if not transcript:
        return "<p>No transcript available for this episode.</p>"
    
    html = []
    lines = transcript.split('\n')
    pending_speaker = None
    
    for line in lines:
        line = line.strip()
        if not line or line == "WEBVTT": continue
        
        speaker = None
        dialogue = line
        
        # 1. Check for bracketed speaker identifiers like "[Speaker Name]"
        bracket_match = re.match(r'^\[([^\]]+)\]\s*(.*)', line)
        if bracket_match:
            speaker = bracket_match.group(1)
            dialogue = bracket_match.group(2)
        # 2. Check for colon speaker identifiers like "Speaker Name:"
        elif ':' in line and len(line.split(':', 1)[0]) < 30:
            parts = line.split(':', 1)
            speaker = parts[0].strip()
            dialogue = parts[1].strip()
        
        # If we found a speaker, format it
        if speaker:
            speaker = format_speaker_name(speaker, author_list)
            
            # If there's no dialogue on this line, buffer the speaker for the next line
            if not dialogue:
                pending_speaker = speaker
                continue
        
        # Use the buffered speaker if we have one and this line didn't have its own
        current_speaker = speaker or pending_speaker
        pending_speaker = None # Reset buffer
        
        if current_speaker:
            html.append(f'''
            <div class="transcript-line">
                <div class="speaker">{escape(current_speaker)}</div>
                <div class="dialogue">{escape(dialogue)}</div>
            </div>''')
        else:
            html.append(f'''
            <div class="transcript-line">
                <div class="dialogue">{escape(dialogue)}</div>
            </div>''')
            
    return '\n'.join(html)

# --- Main Logic ---
def generate():
    episodes = []
    audio_files = glob.glob(os.path.join(AUDIO_DIR, "*.mp3"))
    
    audio_files.sort(key=os.path.getmtime, reverse=True)

    os.makedirs('episodes', exist_ok=True)

    for file_path in audio_files:
        filename = os.path.basename(file_path)
        id3 = read_id3_v2(file_path)
        
        title = id3.get('TIT2') or clean_title(filename)
        author = id3.get('TPE1') or PODCAST_AUTHOR
        description = id3.get('COMM') or f"{title} episode."
        
        # Priority: .vtt file, then .srt file, then USLT tag
        transcript = id3.get('USLT', "")
        vtt_file_path = os.path.splitext(file_path)[0] + '.vtt'
        srt_file_path = os.path.splitext(file_path)[0] + '.srt'
        
        # Automatically convert SRT to VTT if it exists and VTT doesn't
        if os.path.exists(srt_file_path) and not os.path.exists(vtt_file_path):
            srt_to_vtt(srt_file_path)

        transcript_url = None
        transcript_type = None

        if os.path.exists(vtt_file_path):
            transcript_url = f"audio/{os.path.basename(vtt_file_path)}"
            transcript_type = "text/vtt"
            try:
                with open(vtt_file_path, 'r', encoding='utf-8') as vf:
                    # For website, we can use the same parse_srt as it handles the format similarly
                    transcript = parse_srt(vf.read())
            except Exception:
                pass
        elif os.path.exists(srt_file_path):
            transcript_url = f"audio/{os.path.basename(srt_file_path)}"
            transcript_type = "application/x-subrip"
            try:
                with open(srt_file_path, 'r', encoding='utf-8') as sf:
                    transcript = parse_srt(sf.read())
            except Exception:
                pass

        season = id3.get('TPOS')
        episode_num = id3.get('TRCK')
        
        duration_sec = get_mp3_duration(file_path)
        duration_str = format_duration(duration_sec)
        file_size = os.path.getsize(file_path)
        dt = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        pub_date_rss = dt.strftime('%a, %d %b %Y %H:%M:%S +0000')
        pub_date_human = dt.strftime('%B %d, %Y')
        
        slug = slugify(title)
        
        episodes.append({
            'title': title,
            'author': author,
            'description': description,
            'transcript': transcript,
            'transcript_url': transcript_url,
            'transcript_type': transcript_type,
            'season': season,
            'episode_num': episode_num,
            'filename': filename,
            'duration_sec': duration_sec,
            'duration_str': duration_str,
            'file_size': file_size,
            'pub_date_rss': pub_date_rss,
            'pub_date_human': pub_date_human,
            'date': dt,
            'url': f"audio/{filename}",
            'slug': slug,
            'page_url': f"episodes/{slug}.html"
        })

    # --- Sort Episodes (Newest First) ---
    episodes.sort(key=lambda x: x['date'], reverse=True)

    common_styles = f"""
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f1f5f9; line-height: 1.6; margin: 0; padding: 0; }}
        header {{ 
            position: relative;
            width: 100%; 
            height: 300px;
            background: #0f172a; 
            margin-bottom: 3rem;
            border-bottom: 1px solid #334155;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5); 
        }}
        .header-bg {{
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image: url("{LOGO_PATH}");
            background-size: cover;
            background-position: center;
            filter: blur(20px) brightness(0.4);
            transform: scale(1.1);
            z-index: 1;
        }}
        header img.logo {{ 
            position: relative;
            max-height: 70%;
            max-width: 90%;
            width: auto;
            height: auto;
            object-fit: contain;
            display: block;
            z-index: 2;
            border-radius: 0.5rem;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }}
        .tagline {{
            position: absolute;
            bottom: 2rem;
            left: 0;
            right: 0;
            text-align: center;
            z-index: 2;
            color: #f8fafc;
            font-size: 1.1rem;
            font-weight: 500;
            letter-spacing: 0.025em;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        }}

        .container {{ max-width: 800px; margin: 0 auto; padding: 0 2rem 4rem 2rem; }}
        .episode {{ background: #1e293b; border-radius: 1rem; padding: 2rem; margin-bottom: 2rem; border: 1px solid #334155; transition: transform 0.2s; }}
        .episode:hover {{ transform: translateY(-4px); border-color: #38bdf8; }}
        .episode h2 {{ margin-top: 0; color: #f8fafc; font-size: 1.5rem; }}
        .episode h2 a {{ color: inherit; text-decoration: none; }}
        .episode h2 a:hover {{ color: #38bdf8; }}
        .meta {{ font-size: 0.875rem; color: #38bdf8; font-weight: 600; margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        .description {{ margin-top: 1rem; color: #cbd5e1; font-size: 1rem; }}
        audio {{ width: 100%; margin-top: 1.5rem; border-radius: 0.5rem; }}
        footer {{ text-align: center; margin-top: 4rem; padding-top: 2rem; border-top: 1px solid #334155; }}
        .rss-link, .btn {{ display: inline-flex; align-items: center; justify-content: center; gap: 0.75rem; color: #38bdf8; text-decoration: none; font-weight: bold; padding: 0.75rem 1.5rem; border: 2px solid #38bdf8; border-radius: 1rem; transition: all 0.2s; background: transparent; cursor: pointer; }}
        .rss-link img {{ height: 24px; width: auto; border-radius: 1rem; }}
        .rss-link:hover, .btn:hover {{ background: #38bdf8; color: #0f172a; }}
        
        /* Table Styles */
        table {{ width: 100%; border-collapse: collapse; margin-top: 2rem; background: #1e293b; border-radius: 1rem; overflow: hidden; border: 1px solid #334155; }}
        th, td {{ padding: 1rem; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ background: #334155; color: #38bdf8; text-transform: uppercase; font-size: 0.875rem; letter-spacing: 0.05em; }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: #334155; }}
        td a {{ color: #38bdf8; text-decoration: none; font-weight: 600; }}
        td a:hover {{ text-decoration: underline; }}

        /* Transcript Styles */
        .transcript {{ background: transparent; padding: 0; margin-top: 2rem; border: none; }}
        .transcript h3 {{ margin-top: 0; color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; margin-bottom: 1.5rem; }}
        
        .transcript-line {{ background: #1e293b; border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1rem; border: 1px solid #334155; }}
        .speaker {{ color: #38bdf8; font-size: 0.875rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }}
        .dialogue {{ color: #cbd5e1; line-height: 1.6; }}
        
        .back-link {{ display: block; margin-bottom: 2rem; color: #38bdf8; text-decoration: none; font-weight: 600; }}
        .back-link:hover {{ text-decoration: underline; }}
    """

    header_html = f"""
    <header>
        <div class="header-bg"></div>
        <img src="{LOGO_PATH}" alt="{PODCAST_NAME} Logo" class="logo">
    </header>
    """

    footer_html = f"""
        <footer>
            <a href="podcast://hellolunabot.github.io/lunacast/rss.xml" class="rss-link"><img src="{APPLE_PODCASTS_ICON}" alt="Apple Podcasts Icon">Add to Apple Podcasts</a>
        </footer>
    """

    def get_episode_block(ep, is_page=False):
        return f"""
            <div class="episode">
                <div class="meta">
                    {ep['pub_date_human']} | {ep['duration_str']}
                    {f" | Season {ep['season']}" if ep['season'] else ""}
                    {f" | Episode {ep['episode_num']}" if ep['episode_num'] else ""}
                    | Voices: {ep['author']}
                </div>
                <h2>{'<a href="' + ep['page_url'] + '">' if not is_page else ''}{ep['title']}{'</a>' if not is_page else ''}</h2>
                <div class="description">{ep['description']}</div>
                <audio controls>
                    <source src="{'../' if is_page else ''}{ep['url']}" type="audio/mpeg">
                    Your browser does not support the audio element.
                </audio>
            </div>
        """

    # --- Generate individual episode pages ---
    for ep in episodes:
        transcript_html = format_transcript_html(ep['transcript'], ep['author'])
        page_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ep['title']} - {PODCAST_NAME}</title>
    <link rel="icon" type="image/png" href="../{FAVICON_PATH}">

    <!-- Social Sharing Meta Tags -->
    <meta property="og:title" content="{ep['title']} - {PODCAST_NAME}">
    <meta property="og:description" content="{escape(ep['description'], {'"': '&quot;'})}">
    <meta property="og:image" content="{PODCAST_LINK}{THUMBNAIL_PATH}">
    <meta property="og:url" content="{PODCAST_LINK}{ep['page_url']}">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{ep['title']} - {PODCAST_NAME}">
    <meta name="twitter:description" content="{escape(ep['description'], {'"': '&quot;'})}">
    <meta name="twitter:image" content="{PODCAST_LINK}{THUMBNAIL_PATH}">

    <style>
        {common_styles.replace(LOGO_PATH, '../' + LOGO_PATH)}
    </style>
</head>
<body>
    <header>
        <div class="header-bg"></div>
        <img src="../{LOGO_PATH}" alt="{PODCAST_NAME} Logo" class="logo">
    </header>
    
    <div class="container">
        <a href="../index.html" class="back-link">← Back to Home</a>
        <main>
            {get_episode_block(ep, is_page=True)}
            <div class="transcript">
                <h3>Transcript</h3>
                {transcript_html}
            </div>
        </main>
        {footer_html.replace(APPLE_PODCASTS_ICON, '../' + APPLE_PODCASTS_ICON)}
    </div>
</body>
</html>
"""
        with open(ep['page_url'], "w") as f:
            f.write(page_content)

    # --- Generate episodes.html ---
    table_rows = "".join([f"""
        <tr>
            <td><a href="{ep['page_url']}">{ep['title']}</a></td>
            <td>{ep['duration_str']}</td>
            <td>{ep['author']}</td>
            <td>{ep['pub_date_human']}</td>
        </tr>
    """ for ep in episodes])

    episodes_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All Episodes - {PODCAST_NAME}</title>
    <link rel="icon" type="image/png" href="{FAVICON_PATH}">

    <!-- Social Sharing Meta Tags -->
    <meta property="og:title" content="All Episodes - {PODCAST_NAME}">
    <meta property="og:description" content="{PODCAST_DESCRIPTION}">
    <meta property="og:image" content="{PODCAST_LINK}{THUMBNAIL_PATH}">
    <meta property="og:url" content="{PODCAST_LINK}episodes.html">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="All Episodes - {PODCAST_NAME}">
    <meta name="twitter:description" content="{PODCAST_DESCRIPTION}">
    <meta name="twitter:image" content="{PODCAST_LINK}{THUMBNAIL_PATH}">

    <style>
        {common_styles}
    </style>
</head>
<body>
    {header_html}
    
    <div class="container">
        <a href="index.html" class="back-link">← Back to Home</a>
        <main>
            <h1>All Episodes</h1>
            <table>
                <thead>
                    <tr>
                        <th>Title</th>
                        <th>Duration</th>
                        <th>Voices</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </main>
        {footer_html}
    </div>
</body>
</html>
"""
    with open("episodes.html", "w") as f:
        f.write(episodes_html)

    # --- Generate index.html ---
    recent_episodes = episodes[:5]
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{PODCAST_NAME}</title>
    <link rel="icon" type="image/png" href="{FAVICON_PATH}">

    <!-- Social Sharing Meta Tags -->
    <meta property="og:title" content="{PODCAST_NAME}">
    <meta property="og:description" content="{PODCAST_DESCRIPTION}">
    <meta property="og:image" content="{PODCAST_LINK}{THUMBNAIL_PATH}">
    <meta property="og:url" content="{PODCAST_LINK}">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{PODCAST_NAME}">
    <meta name="twitter:description" content="{PODCAST_DESCRIPTION}">
    <meta name="twitter:image" content="{PODCAST_LINK}{THUMBNAIL_PATH}">

    <style>
        {common_styles}
    </style>
</head>
<body>
    {header_html}
    
    <div class="container">
        <main>
            {"".join([get_episode_block(ep) for ep in recent_episodes])}
            
            <div style="text-align: center; margin-top: 2rem;">
                <a href="episodes.html" class="btn">View All Episodes</a>
            </div>
        </main>

        {footer_html}
    </div>
</body>
</html>
"""
    with open("index.html", "w") as f:
        f.write(html_template)

    # --- Generate rss.xml ---
    rss_items = []
    # Current timestamp for lastBuildDate and cache busting
    now = datetime.datetime.now(datetime.timezone.utc)
    build_date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
    version_ts = int(now.timestamp())

    for ep in episodes:
        extra_tags = [
            f"<itunes:explicit>false</itunes:explicit>"
        ]
        if ep['season']: extra_tags.append(f"<itunes:season>{ep['season']}</itunes:season>")
        if ep['episode_num']: extra_tags.append(f"<itunes:episode>{ep['episode_num']}</itunes:episode>")
        if ep['transcript_url']: 
            extra_tags.append(f'<podcast:transcript url="{PODCAST_LINK}{ep["transcript_url"]}" type="{ep["transcript_type"]}" language="en" rel="transcript"/>')
        
        itunes_tags = "\n            ".join(extra_tags)
        if itunes_tags:
            itunes_tags = "\n            " + itunes_tags

        # Escape characters for XML
        e_title = escape(ep['title'])
        e_author = escape(ep['author'])
        e_description = escape(ep['description'])
        
        # Ensure pubDate uses GMT for maximum RFC 2822 compatibility
        pub_date_rss = ep['date'].strftime('%a, %d %b %Y %H:%M:%S GMT')

        rss_items.append(f"""
        <item>
            <title>{e_title}</title>
            <itunes:title>{e_title}</itunes:title>
            <itunes:summary>{e_description}</itunes:summary>
            <itunes:episodeType>full</itunes:episodeType>
            <link>{PODCAST_LINK}{ep['page_url']}</link>
            <itunes:author>{e_author}</itunes:author>
            <description>{e_description}</description>
            <pubDate>{pub_date_rss}</pubDate>
            <enclosure url="{PODCAST_LINK}{ep['url']}" length="{ep['file_size']}" type="audio/mpeg"/>
            <itunes:duration>{ep['duration_sec']}</itunes:duration>
            <itunes:image href="{PODCAST_LINK}{THUMBNAIL_PATH}"/>
            <guid isPermaLink="false">{ep['filename']}</guid>{itunes_tags}
        </item>""")


    rss_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
    xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" 
    xmlns:content="http://purl.org/rss/1.0/modules/content/"
    xmlns:podcast="https://podcastindex.org/">
    <channel>
        <title>{escape(PODCAST_NAME)}</title>
        <link>{PODCAST_LINK}</link>
        <lastBuildDate>{build_date}</lastBuildDate>
        <language>en</language>
        <copyright>&#169; {datetime.datetime.now().year} {escape(PODCAST_AUTHOR)}</copyright>
        <itunes:author>{escape(PODCAST_AUTHOR)}</itunes:author>
        <description>{escape(PODCAST_DESCRIPTION)}</description>
        <itunes:type>episodic</itunes:type>
        <itunes:owner>
            <itunes:name>{escape(PODCAST_AUTHOR)}</itunes:name>
            <itunes:email>lunabot@hellolunabot.com</itunes:email>
        </itunes:owner>
        <itunes:image href="{PODCAST_LINK}{THUMBNAIL_PATH}"/>
        <itunes:category text="Technology"/>
        <itunes:explicit>false</itunes:explicit>
        {"".join(rss_items)}
    </channel>
</rss>
"""
    with open("rss.xml", "w") as f:
        f.write(rss_template)

    print(f"Generated index.html and rss.xml with {len(episodes)} episodes.")

if __name__ == "__main__":
    generate()
