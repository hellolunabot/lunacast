# LunaCast: Static Podcast Generator

LunaCast is a zero-dependency static site and RSS feed generator for the "LunaCast" podcast. It transforms MP3 files and their metadata into a polished landing page, individual episode pages with interactive transcripts, and a valid podcast feed.

## Project Overview

- **Purpose**: Automate the generation of a podcast website and RSS feed from audio files.
- **Core Technology**: Python 3 (Standard Library only).
- **Architecture**: A single-script generator (`generate_site.py`) that performs the following:
    - Scans the `episodes/` directory for subdirectories containing `podcast.mp3`.
    - Parses ID3v2.3 and ID3v2.4 tags using a custom-built parser to extract titles, authors, summaries, and dates.
    - Automatically converts `.srt` transcripts to `.vtt` for platform compatibility.
    - Estimates audio duration by analyzing MPEG frame headers.
    - Normalizes speaker names in transcripts using artist metadata.
    - Renders HTML (Home, All Episodes, and Episode-specific pages) and XML templates using Python f-strings.

## Building and Running

### Generate the Site
To scan the episode files and update the website and RSS feed, run:
```bash
python3 generate_site.py
```

### Dependencies
This project has **no external dependencies**. Do not introduce libraries like `mutagen`, `eyeD3`, or `lxml`. Always use standard library modules (`os`, `glob`, `struct`, `xml.sax.saxutils`, etc.).

## Project Structure

- `episodes/`: Source directory for podcast episodes.
    - `[episode-slug]/`: Subdirectory for a specific episode.
        - `podcast.mp3`: The main audio file (Required).
        - `subtitles.vtt` or `subtitles.srt`: Transcript file. SRT is auto-converted to VTT.
        - `script.md`: Optional episode description; takes priority over ID3 `COMM` tag.
        - `index.html`: Generated episode-specific page with interactive transcript.
- `images/`: Brand assets, icons, and thumbnails.
- `index.html`: Generated landing page (shows 5 most recent episodes).
- `episodes.html`: Generated list of all episodes.
- `rss.xml`: Generated podcast feed.

## Development Conventions

### Metadata & ID3 Tags
The generator relies on specific ID3 frames:
- `TIT2`: Episode Title (fallback: cleaned slug).
- `TPE1`: Artist (displayed as "Voices"). Used to normalize speaker names in transcripts.
- `COMM` or `TXXX:comment`: Episode Summary (fallback if `script.md` is missing).
- `TPOS`: Season number.
- `TRCK`: Episode number.
- `TDRC`: Publication Date (fallback: file modification time).
- `USLT`: Unsynchronized transcript (fallback if no `.vtt` or `.srt` file is found).

### Transcripts & Interactivity
- Episode pages feature interactive transcripts that highlight the current speaker and allow users to click a line to seek the audio.
- Speaker names are normalized: e.g., mapping `ALISTAIRTHORNE` to `ALISTAIR THORNE` based on the `TPE1` (Voices) metadata.

### XML & RSS Validity
- All text content inserted into `rss.xml` **must** be escaped using `xml.sax.saxutils.escape`.
- The feed includes standard iTunes tags and `podcastindex.org` transcript tags.

### Design & Styling
- **Visuals**: Modern dark theme with blur-effect headers and responsive layouts.
- **Consistency**: Buttons and containers use a `border-radius` of `1rem`.

## Workflow

- **Commits & Pushes**: NEVER commit or push changes without explicit instruction from the user.
- **Commit Protocol**:
    1. **Gather**: Run `git status` and `git diff` to review all changes (including generated files).
    2. **Propose**: Present a draft commit message and a list of files to be staged for user review.
    3. **Execute**: Only run `git commit` and `git push` after the user has explicitly confirmed the draft.
