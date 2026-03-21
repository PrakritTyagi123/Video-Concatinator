# 🎬 Video Timeline Editor

A desktop application for creating and exporting multiple video timelines with GPU-accelerated encoding.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- **Multiple Timelines** – Create, rename, and manage multiple video timelines simultaneously
- **Drag & Drop** – Intuitive drag-and-drop interface for adding and reordering clips
- **GPU Acceleration** – Auto-detects and uses the best available encoder (NVIDIA, AMD, Intel, Apple)
- **Smart Export** – Automatically chooses between fast concat (copy) or re-encoding based on source formats
- **Live Progress** – Real-time progress bar with ETA during export
- **Dark/Light Theme** – Toggle between themes with preference saved locally

## Supported Encoders

The application automatically detects and uses the best available encoder in this priority order:

| Priority | Encoder | Description |
|----------|---------|-------------|
| 1 | `av1_nvenc` | NVIDIA AV1 |
| 2 | `av1_qsv` | Intel QuickSync AV1 |
| 3 | `av1_amf` | AMD AV1 |
| 4 | `av1_videotoolbox` | Apple VideoToolbox AV1 |
| 5 | `libaom-av1` | CPU AV1 (software) |
| 6 | `h264_nvenc` | NVIDIA H.264 |
| 7 | `h264_amf` | AMD H.264 |
| 8 | `h264_videotoolbox` | Apple H.264 |
| 9 | `libx264` | CPU H.264 (fallback) |

## Requirements

### System Requirements

- **Python** 3.10 or higher
- **FFmpeg** (must be in system PATH)
- **Google Chrome** (recommended) or any Chromium-based browser

### Python Dependencies

```bash
pip install eel
```

## Installation

1. **Clone or download** the project files

2. **Ensure folder structure:**
   ```
   video-timeline-editor/
   ├── main.py
   └── web/
       ├── index.html
       ├── app.js
       └── styles.css
   ```

3. **Install FFmpeg:**
   - **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, and add `bin` folder to PATH
   - **macOS:** `brew install ffmpeg`
   - **Linux:** `sudo apt install ffmpeg`

4. **Install Python dependencies:**
   ```bash
   pip install eel
   ```

## Usage

### Starting the Application

```bash
cd video-timeline-editor
python main.py
```

The application will:
1. Detect available GPU encoders
2. Open a Chrome window with the UI
3. Display the detected encoder in the console

### Workflow

1. **Select Source Folder** – Click to choose a folder containing video files
2. **Create Timelines** – Click "Add New Timeline" to create timelines
3. **Add Videos** – Drag videos from the library to timelines, or use the "+All" button
4. **Reorder Clips** – Drag clips within or between timelines to reorder
5. **Select Destination** – Choose where to save exported files
6. **Export** – Click "Export All Timelines" to render

### Supported Video Formats

`.mp4`, `.mov`, `.mkv`, `.avi`, `.flv`, `.webm`, `.ts`

## Project Structure

```
video-timeline-editor/
├── main.py          # Python backend (Eel server, FFmpeg processing)
└── web/
    ├── index.html   # HTML structure
    ├── app.js       # Frontend JavaScript (state, drag-drop, UI logic)
    └── styles.css   # Styling with light/dark theme support
```

### File Descriptions

| File | Description |
|------|-------------|
| `main.py` | Backend server using Eel framework. Handles file dialogs, GPU detection, FFmpeg encoding, and progress streaming. |
| `index.html` | Main HTML template with sidebar (source/destination pickers, export controls) and main panel (timelines). |
| `app.js` | Frontend logic including state management, drag-and-drop handling, theme toggle, and Eel communication. |
| `styles.css` | Complete styling with CSS variables, animations, and full dark theme support. |

## API Reference

### Python → JavaScript (Exposed Functions)

| Function | Description |
|----------|-------------|
| `choose_source()` | Opens folder picker, returns `{path, files[]}` |
| `choose_destination()` | Opens folder picker, returns path string |
| `export_timelines(json, path)` | Exports timelines to specified directory |
| `get_system_info()` | Returns encoder info and GPU status |

### JavaScript → Python (Eel Callbacks)

| Function | Description |
|----------|-------------|
| `start_timeline(name)` | Called when a timeline export begins |
| `update_progress(percent, name, eta)` | Called with progress updates during export |

## Export Behavior

### Fast Mode (Stream Copy)
When all clips in a timeline share the same format, the app uses FFmpeg's concat demuxer with stream copy (`-c copy`). This is:
- ⚡ Extremely fast
- 📦 No quality loss
- 💾 No re-encoding required

### Re-encode Mode
When clips have different formats, the app re-encodes using the detected GPU encoder with:
- Optimized presets for each encoder type
- Quality settings (CRF 23-30 depending on encoder)
- AAC audio at 128kbps

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Chrome not found" | Install Chrome, or modify `mode="chrome"` to `mode=None` in `main.py` |
| FFmpeg not found | Ensure FFmpeg is in PATH: run `ffmpeg -version` to verify |
| No GPU acceleration | App falls back to CPU encoding automatically |
| Tkinter errors (Linux) | Install: `sudo apt install python3-tk` |
| Export fails | Check console for FFmpeg error messages |

## Configuration

### Changing Default Window Size

In `main.py`, modify the `eel.start()` call:
```python
eel.start("index.html", size=(1380, 900), ...)
```

### Changing Browser Mode

```python
# Use default browser instead of Chrome
eel.start("index.html", mode=None, ...)

# Use Edge
eel.start("index.html", mode="edge", ...)
```

## License

MIT License - Feel free to use, modify, and distribute.

## Acknowledgments

- [Eel](https://github.com/python-eel/Eel) – Python library for creating desktop apps with web UI
- [FFmpeg](https://ffmpeg.org/) – Multimedia processing framework