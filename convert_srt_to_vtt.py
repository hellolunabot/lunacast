import os
import re

def srt_to_vtt(srt_path):
    vtt_path = srt_path.replace('.srt', '.vtt')
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Header
    vtt_content = "WEBVTT\n\n"
    
    # 2. Convert timestamps (comma to dot ONLY in timestamps)
    # We use a regex to target only the timestamps: 00:00:00,000 --> 00:00:12,179
    def fix_timestamp(match):
        return match.group(0).replace(',', '.')
    
    content = re.sub(r'\d{2}:\d{2}:\d{2},\d{3}', fix_timestamp, content)
    
    # 3. Remove SRT index numbers (not required in VTT)
    content = re.sub(r'^\d+\s*\n(?=\d{2}:\d{2}:\d{2})', '', content, flags=re.MULTILINE)
    
    vtt_content += content.strip() + "\n"
    
    with open(vtt_path, 'w', encoding='utf-8') as f:
        f.write(vtt_content)
    print(f"Converted {srt_path} to {vtt_path}")

if __name__ == "__main__":
    audio_dir = 'audio'
    for file in os.listdir(audio_dir):
        if file.endswith('.srt'):
            srt_to_vtt(os.path.join(audio_dir, file))
