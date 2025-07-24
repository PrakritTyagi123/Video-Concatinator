
# 🎬 Video Timeline Editor

*A lightweight, desktop‑friendly tool for assembling and exporting one‑or‑many video timelines.*

Drag clips in, reorder on the fly, and export in ultra‑fast **copy** mode *or* full **GPU‑accelerated re‑encode**—no NLE bloat and no command‑line gymnastics.

---

## ✨ Key Features

| Capability | Details |
|------------|---------|
| **Automatic GPU detection** | Picks the best available encoder (NVENC / AMF / VideoToolbox, falling back to libx264). |
| **Smart export pipeline** | • **Copy‑fast** if every clip already matches container+codec  <br>• **GPU re‑encode** when codecs/resolutions differ. |
| **Drag‑and‑drop timeline builder** | Add clips from the library, reorder, or duplicate between timelines using intuitive HTML5 DnD. |
| **Multiple parallel timelines** | Create as many timelines as you want; export all with one click. |
| **Light / Dark theme toggle** | Persists in `localStorage`—perfect for night sessions. |
| **Live progress & ETA** | FFmpeg `‑progress` is parsed and streamed to the UI so you always know where you stand. |
| **Bulk “Add to all timelines”** | Great for universal intros/outros. |
| **Zero‑install front‑end** | Bundled with [Eel](https://github.com/ChrisKnott/Eel); launches in Chrome on Windows or system browser elsewhere. |

---

## 📦 Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Python 3.9 +** | Tested on 3.11. |
| **FFmpeg (static build)** | Must include NVENC/AMF/VideoToolbox if you want GPU encode. |
| **NVIDIA / AMD / Apple drivers** | Match your FFmpeg build for hardware‑encode support. |
| **Google Chrome** (Windows only) | Eel opens in Chrome for best ES6 / CSS support. |

---

## 🚀 Quick Start

```bash
git clone https://github.com/<your‑user>/video‑timeline‑editor.git
cd video‑timeline‑editor

python -m venv .venv
# PowerShell
.venv\Scripts\Activate.ps1
# or bash
source .venv/bin/activate

pip install -r requirements.txt      # eel, tqdm, ffmpeg‑progress, etc.
python main.py
```

1. **Select Source Folder** – loads every `.mp4`, `.mkv`, etc. in one go.  
2. **Drag clips** from the library onto a timeline (create more timelines as needed).  
3. **Pick Destination Folder**.  
4. Hit **🚀 Export All Timelines**.  
   *If clips share container *and* codec the app “copy‑fast” concatenates them; otherwise it re‑encodes using the detected GPU encoder.*

---

## 🛠 Advanced Options

| Trick | How |
|-------|-----|
| **Force re‑encode** | Pass `--force` flag (coming soon) or add a UI checkbox; forces the GPU branch even when copy‑fast is possible. |
| **Custom NVENC bitrate** | Edit the `cmd.extend([...])` block in `exporter.py::_export_with_reencoding`. |
| **Package into a single EXE / App** | `pip install pyinstaller` then `pyinstaller --onefile main.py` (ship the `web/` folder and FFmpeg DLLs alongside). |
| **Disable GPU** | Start with environment variable `VTE_CPU=1` to bypass GPU detection. |

---

## 🐛 Troubleshooting

| Symptom | Possible Fix |
|---------|--------------|
| **“Missing files detected”** | Paths in the timeline no longer exist—remove and re‑add the clips. |
| **GPU encoder not used** | The export fell back to copy‑fast because every clip already matched container+codec; force a re‑encode to exercise the GPU. |
| **No progress bar** | Ensure you’re running FFmpeg ≥ 3.1 (adds `‑progress pipe:1`). |

---

## 🗺 Roadmap

- Waveform & VU‑meter overlay  
- Undo/redo stack  
- Basic audio ducking  
- Render presets (YouTube 4K, Twitch 1080p60, etc.)  
- One‑click installer  

---

## 🤝 Contributing

1. Fork → feature branch → PR.  
2. Follow PEP‑8; run `ruff .` before committing.  
3. Large UI changes? Attach a short screen‑cap GIF (link only, no images in the repo).

---

## 📄 License

[MIT](LICENSE)

---

**Happy cutting!**
