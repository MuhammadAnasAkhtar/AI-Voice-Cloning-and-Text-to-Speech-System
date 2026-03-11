# 🎙️ Voice Studio — Premium TTS Web Application

A professional text-to-speech web application with voice cloning, custom voice creation, and multi-language support.

## Features

- **🧬 Voice Cloning** — Upload your voice once, generate speech that sounds like you
- **🎤 Custom Voice** — Create and manage voice profiles with AI analysis
- **🔊 Normal Voices** — Quick TTS with 14 languages and 30+ built-in voices
- **📚 Voice Library** — Browse all available voices across languages
- **📄 100K Words** — Process very large documents with auto-chunking
- **🎭 10 Styles** — Natural, Newsreader, Documentary, Calm, Energetic, etc.
- **⚙️ Fine-tune** — Adjust timbre, tempo, and pitch
- **🌙 Premium Dark UI** — Professional, responsive interface

## Requirements

- Python 3.9+
- ffmpeg (must be installed and in PATH)

## Quick Start

```bash
# 1. Install ffmpeg (if not installed)
# Windows: choco install ffmpeg  OR  download from ffmpeg.org
# Mac:     brew install ffmpeg
# Linux:   sudo apt install ffmpeg

# 2. Install Python packages
pip install -r requirements.txt

# 3. Run the server
python app.py

# 4. Open in browser
# http://127.0.0.1:5000
```

## Project Structure

```
VoiceStudio/
├── app.py                  # Flask backend (all TTS logic)
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html          # Main HTML page
├── static/
│   ├── css/style.css       # Premium dark theme
│   ├── js/app.js           # Frontend JavaScript
│   ├── uploads/            # Temp uploaded files
│   └── output/             # Generated audio files
└── profiles/               # Saved voice profiles
```

## How to Use

1. **Normal Voices**: Go to "Normal Voices" tab → pick language/voice/style → type text → Generate
2. **Custom Voice**: Go to "Custom Voice" tab → upload a 15-30 second voice recording → Save
3. **Voice Cloning**: Go to "Voice Cloning" tab → select your voice profile → type text → Generate
