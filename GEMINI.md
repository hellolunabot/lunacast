# LunaCast: Static Podcast Generator

LunaCast is a zero-dependency static site and RSS feed generator for the "LunaCast" podcast. It transforms MP3 files and their embedded metadata into a polished landing page and a valid podcast feed.

## Project Overview

- **Purpose**: Automate the generation of a podcast website (`index.html`) and RSS feed (`rss.xml`) from audio files.
- **Core Technology**: Python 3 (Standard Library only).
- **Architecture**: A single-script generator (`generate_site.py`) that performs the following:
    - Scans the `audio/` directory for MP3 files.
    - Parses ID3v2.3 and ID3v2.4 tags using a custom-built parser to extract titles, authors, and summaries.
    - Automatically converts `.srt` transcripts to `.vtt` for platform compatibility.
    - Estimates audio duration by analyzing MPEG frame headers.
    - Renders HTML and XML templates using Python f-strings.

## Building and Running

### Generate the Site
To scan the audio files and update the website and RSS feed, run:
```bash
python3 generate_site.py
```

### Dependencies
This project has **no external dependencies**. Do not introduce libraries like `mutagen`, `eyeD3`, or `lxml`. Always use standard library modules (`os`, `glob`, `struct`, `xml.sax.saxutils`, etc.).

## Development Conventions

### Metadata & ID3 Tags
The generator relies on specific ID3 frames:
- `TIT2`: Episode Title.
- `TPE1`: Artist (displayed as "Voices" on the website). These are used to normalize and format speaker names in the transcript (e.g., mapping `ALISTAIRTHORNE` to `ALISTAIR THORNE`).
- `COMM` or `TXXX:comment`: Episode Summary.
- `TPOS` / `TRCK`: Season and Episode numbers.
- `USLT`: Embedded transcript (fallback if no `.vtt` or `.srt` file is found).

### XML & RSS Validity
- All text content inserted into `rss.xml` **must** be escaped using `xml.sax.saxutils.escape` to ensure the feed is valid.
- The project uses the `podcast://` URL scheme for direct subscription links, which deep-links into the Apple Podcasts app.

### Design & Styling
- **Visual Consistency**: The "Add to Apple Podcasts" button and its icon should use a `border-radius` of `1rem` to match the episode containers.
- **Flexbox**: Use `inline-flex` for UI elements that combine icons and text for consistent vertical alignment.

### Automated Tests
Currently, the project uses manual verification and structural checks (e.g., `xml.etree.ElementTree` parsing) to ensure correctness.

## Workflow

- **Commits & Pushes**: NEVER commit or push changes without explicit instruction from the user.
- **Commit Protocol**:
    1. **Gather**: Run `git status` and `git diff` to review all changes (including generated files).
    2. **Propose**: Present a draft commit message and a list of files to be staged for user review.
    3. **Execute**: Only run `git commit` and `git push` after the user has explicitly confirmed the draft.
