# LunaCast

A cosmic journey through space and time.

This is a static podcast site and RSS feed generator.

## How it works

The site is generated from the MP3 files located in the `audio/` directory.

## Getting Started

1.  **Add Episodes**: Drop your `.mp3` files into the `audio/` folder.
2.  **Configuration**: Open `generate_site.py` and update the `PODCAST_LINK` variable to your GitHub Pages URL (e.g., `https://username.github.io/LunaCast/`).
3.  **Generate Site**: Run the generator script:
    ```bash
    python3 generate_site.py
    ```
4.  **Publish**: Commit and push the generated `index.html` and `rss.xml` to your GitHub repository.

## Assets
- `images/lunacast-logo.png`: Used on the website.
- `images/lunacast-thumbnail.jpg`: Used for the Apple Podcasts / RSS feed thumbnail.

## Requirements
- Python 3.x (No external dependencies required!)
