<!-- badges (optional) -->
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Issues](https://img.shields.io/github/issues/🔧YOUR_USER/🔧YOUR_REPO)

# 🎬 Video Timeline Editor

Drag‑and‑drop desktop app that turns loose clips into ready‑to‑upload videos.


## ✨ Features

| | |
|---|---|
| 🔄 **Re‑order clips** by simply dragging them inside a timeline | 🌙 **One‑click dark mode** (saved in `localStorage`) |
| ⚡ **Stream‑copy export** (instant if codecs match) with automatic re‑encode fallback | 🪄 **Real progress bar & ETA** for every timeline |
| 📁 **Cross‑platform** (Windows / macOS / Linux) — powered by Python + Eel + FFmpeg | 💾 **No installation** beyond Python+FFmpeg — just run `python main.py` |

---

## 🚀 Quick Start

```bash
git clone https://github.com/🔧YOUR_USER/video-timeline.git
cd video-timeline

# (optional) create venv, then:
pip install -r requirements.txt   # eel==0.17.0

# FFmpeg must be on PATH
python main.py
