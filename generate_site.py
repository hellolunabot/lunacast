import os
import glob
import datetime
import struct
import base64
from xml.sax.saxutils import escape

# --- Configuration ---
PODCAST_NAME = "LunaCast"
PODCAST_DESCRIPTION = "A cosmic journey through space and time."
PODCAST_AUTHOR = "LunaBot"
PODCAST_LINK = "https://hellolunabot.github.io/lunacast/"
LOGO_PATH = "images/lunacast-logo.png"
THUMBNAIL_PATH = "images/lunacast-thumbnail.jpg"
APPLE_PODCASTS_ICON = "images/apple-podcasts.png"
AUDIO_DIR = "audio"

# --- Metadata Helpers ---
def read_id3_v2(file_path):
    """Basic ID3v2 tag parser for Title, Artist, and Comment."""
    tags = {}
    try:
        with open(file_path, 'rb') as f:
            header = f.read(10)
            if header[:3] != b'ID3':
                return tags
            
            # Size is 4 bytes, synchsafe (ignore the most significant bit of each byte)
            size = (header[6] << 21) | (header[7] << 14) | (header[8] << 7) | header[9]
            tag_data = f.read(size)
            
            i = 0
            while i < len(tag_data) - 10:
                frame_id = tag_data[i:i+4].decode('ascii', errors='ignore')
                if not frame_id or frame_id[0] == '\x00': break
                
                frame_size = struct.unpack('>I', tag_data[i+4:i+8])[0]
                # ID3v2.3 size is standard, ID3v2.4 is synchsafe. Assuming v2.3 for simplicity.
                
                content = tag_data[i+10:i+10+frame_size]
                if frame_id in ['TIT2', 'TPE1', 'COMM', 'TPOS', 'TRCK']:
                    # First byte is encoding (0=ISO-8859-1, 1=UTF-16, 2=UTF-16BE, 3=UTF-8)
                    encoding = content[0]
                    text_data = content[1:]
                    
                    if encoding == 0: text = text_data.decode('iso-8859-1', errors='ignore')
                    elif encoding == 1: text = text_data.decode('utf-16', errors='ignore')
                    elif encoding == 2: text = text_data.decode('utf-16-be', errors='ignore')
                    elif encoding == 3: text = text_data.decode('utf-8', errors='ignore')
                    else: text = text_data.decode('ascii', errors='ignore')
                    
                    # COMM frames have a language and short description before the actual text
                    if frame_id == 'COMM':
                        parts = text.split('\x00', 1)
                        text = parts[-1] if len(parts) > 1 else text
                    
                    # TPOS and TRCK can be "1/10" format, we just want the number
                    clean_text = text.strip('\x00').strip()
                    if frame_id in ['TPOS', 'TRCK'] and '/' in clean_text:
                        clean_text = clean_text.split('/')[0]
                    
                    tags[frame_id] = clean_text
                
                i += 10 + frame_size
    except Exception:
        pass
    return tags

def get_mp3_duration(file_path):
    """Estimate MP3 duration in seconds without external dependencies."""
    try:
        size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            # Look for the first frame sync (0xFFE or 0xFFF)
            data = f.read(8192) # Read more to skip potential large ID3 tags
            for i in range(len(data) - 4):
                if data[i] == 0xFF and (data[i+1] & 0xE0) == 0xE0:
                    header = data[i:i+4]
                    br_index = (header[2] >> 4) & 0x0F
                    bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
                    bitrate = bitrates[br_index]
                    if bitrate > 0:
                        return int(size * 8 / (bitrate * 1000))
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

# --- Main Logic ---
def generate():
    episodes = []
    audio_files = glob.glob(os.path.join(AUDIO_DIR, "*.mp3"))
    
    audio_files.sort(key=os.path.getmtime, reverse=True)

    for file_path in audio_files:
        filename = os.path.basename(file_path)
        id3 = read_id3_v2(file_path)
        
        title = id3.get('TIT2') or clean_title(filename)
        author = id3.get('TPE1') or PODCAST_AUTHOR
        description = id3.get('COMM') or f"{title} episode."
        season = id3.get('TPOS')
        episode_num = id3.get('TRCK')
        
        duration_sec = get_mp3_duration(file_path)
        duration_str = format_duration(duration_sec)
        file_size = os.path.getsize(file_path)
        dt = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        pub_date_rss = dt.strftime('%a, %d %b %Y %H:%M:%S +0000')
        pub_date_human = dt.strftime('%B %d, %Y')
        
        episodes.append({
            'title': title,
            'author': author,
            'description': description,
            'season': season,
            'episode_num': episode_num,
            'filename': filename,
            'duration_sec': duration_sec,
            'duration_str': duration_str,
            'file_size': file_size,
            'pub_date_rss': pub_date_rss,
            'pub_date_human': pub_date_human,
            'date': dt,
            'url': f"audio/{filename}"
        })

    # --- Sort Episodes (Newest First) ---
    episodes.sort(key=lambda x: x['date'], reverse=True)

    # --- Generate index.html ---
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{PODCAST_NAME}</title>
    <style>
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
            max-height: 80%;
            max-width: 90%;
            width: auto;
            height: auto;
            object-fit: contain;
            display: block;
            z-index: 2;
            border-radius: 0.5rem;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 0 2rem 4rem 2rem; }}
        .episode {{ background: #1e293b; border-radius: 1rem; padding: 2rem; margin-bottom: 2rem; border: 1px solid #334155; transition: transform 0.2s; }}
        .episode:hover {{ transform: translateY(-4px); border-color: #38bdf8; }}
        .episode h2 {{ margin-top: 0; color: #f8fafc; font-size: 1.5rem; }}
        .meta {{ font-size: 0.875rem; color: #38bdf8; font-weight: 600; margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        .description {{ margin-top: 1rem; color: #cbd5e1; font-size: 1rem; }}
        audio {{ width: 100%; margin-top: 1.5rem; border-radius: 0.5rem; }}
        footer {{ text-align: center; margin-top: 4rem; padding-top: 2rem; border-top: 1px solid #334155; }}
        .rss-link {{ display: inline-flex; align-items: center; gap: 0.75rem; color: #38bdf8; text-decoration: none; font-weight: bold; padding: 0.75rem 1.5rem; border: 2px solid #38bdf8; border-radius: 1rem; transition: all 0.2s; }}
        .rss-link img {{ height: 24px; width: auto; border-radius: 1rem; }}
        .rss-link:hover {{ background: #38bdf8; color: #0f172a; }}
    </style>
</head>
<body>
    <header>
        <div class="header-bg"></div>
        <img src="{LOGO_PATH}" alt="{PODCAST_NAME} Logo" class="logo">
    </header>
    
    <div class="container">
        <main>
            {"".join([f'''
            <div class="episode">
                <div class="meta">
                    {ep['pub_date_human']} | {ep['duration_str']}
                    {f" | Season {ep['season']}" if ep['season'] else ""}
                    {f" | Episode {ep['episode_num']}" if ep['episode_num'] else ""}
                </div>
                <h2>{ep['title']}</h2>
                <div class="description">{ep['description']}</div>
                <audio controls>
                    <source src="{ep['url']}" type="audio/mpeg">
                    Your browser does not support the audio element.
                </audio>
            </div>
            ''' for ep in episodes])}
        </main>

        <footer>
            <a href="pcasts://hellolunabot.github.io/lunacast/rss.xml" class="rss-link"><img src="{APPLE_PODCASTS_ICON}" alt="Apple Podcasts Icon">Add to Apple Podcasts</a>
        </footer>
    </div>
</body>
</html>
"""
    with open("index.html", "w") as f:
        f.write(html_template)

    # --- Generate rss.xml ---
    rss_items = []
    for ep in episodes:
        itunes_tags = ""
        if ep['season']: itunes_tags += f"<itunes:season>{ep['season']}</itunes:season>"
        if ep['episode_num']: itunes_tags += f"<itunes:episode>{ep['episode_num']}</itunes:episode>"
        
        # Escape characters for XML
        e_title = escape(ep['title'])
        e_author = escape(ep['author'])
        e_description = escape(ep['description'])

        rss_items.append(f"""
        <item>
            <title>{e_title}</title>
            <itunes:author>{e_author}</itunes:author>
            <description>{e_description}</description>
            <pubDate>{ep['pub_date_rss']}</pubDate>
            <enclosure url="{PODCAST_LINK}{ep['url']}" length="{ep['file_size']}" type="audio/mpeg"/>
            <itunes:duration>{ep['duration_sec']}</itunes:duration>
            <itunes:image href="{PODCAST_LINK}{THUMBNAIL_PATH}"/>
            <guid isPermaLink="false">{ep['filename']}</guid>
            {itunes_tags}
        </item>""")


    rss_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
    xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" 
    xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel>
        <title>{escape(PODCAST_NAME)}</title>
        <link>{PODCAST_LINK}</link>
        <language>en-us</language>
        <copyright>&#169; {datetime.datetime.now().year} {escape(PODCAST_AUTHOR)}</copyright>
        <itunes:author>{escape(PODCAST_AUTHOR)}</itunes:author>
        <description>{escape(PODCAST_DESCRIPTION)}</description>
        <itunes:type>episodic</itunes:type>
        <itunes:owner>
            <itunes:name>{escape(PODCAST_AUTHOR)}</itunes:name>
            <itunes:email>contact@example.com</itunes:email>
        </itunes:owner>
        <itunes:image href="{PODCAST_LINK}{THUMBNAIL_PATH}"/>
        <itunes:category text="Technology"/>
        <itunes:explicit>no</itunes:explicit>
        {"".join(rss_items)}
    </channel>
</rss>
"""
    with open("rss.xml", "w") as f:
        f.write(rss_template)

    print(f"Generated index.html and rss.xml with {len(episodes)} episodes.")

if __name__ == "__main__":
    generate()
