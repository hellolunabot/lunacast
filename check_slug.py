#!/usr/bin/env python3
"""Slugify the episode title and check for conflicts."""
import re
import os

title = "The Lone Gunmen at 25: The Show That Predicted 9/11"

# Slugify: lowercase, replace non-alphanumeric with hyphens, collapse, strip
slug = title.lower()
slug = re.sub(r'[^a-z0-9]+', '-', slug)
slug = re.sub(r'-+', '-', slug)
slug = slug.strip('-')
slug = slug + '.mp3'

print(f"Title: {title}")
print(f"Slug:  {slug}")

# Check for existing file
audio_dir = "/opt/data/LunaCast/audio"
existing = os.path.join(audio_dir, slug)
if os.path.exists(existing):
    print(f"CONFLICT: {existing} already exists!")
else:
    print(f"No conflict — safe to use {slug}")
