#!/usr/bin/env python3
"""
Video Timeline Editor – backend
✓ Writes AV1 in an MKV container
✓ Auto-detects the best available GPU encoder (AV1 → H.264 → CPU)
✓ Streams live progress updates to the Eel front-end
"""

import os, json, math, subprocess, tempfile, tkinter as tk, warnings
from tkinter import filedialog
import eel

# --------------------------------------------------------------------------- #
#  Initialisation
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")
eel.init("web", allowed_extensions=[".js", ".html", ".css"])

VIDEO_EXT = (".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm")

# --------------------------------------------------------------------------- #
#  GPU / codec detection
def detect_gpu_encoder() -> tuple[str, str]:
    """
    Probe encoders; return (ffmpeg_name, human_name).
    Order: AV1 (GPU→CPU) then H.264 (GPU→CPU).
    """
    encoders_to_test = [
        ("av1_nvenc",        "NVIDIA AV1"),
        ("av1_qsv",          "Intel QSV AV1"),
        ("av1_amf",          "AMD AV1"),
        ("av1_videotoolbox", "Apple VT AV1"),
        ("libaom-av1",       "CPU AV1"),
        ("h264_nvenc",       "NVIDIA NVENC (H.264)"),
        ("h264_amf",         "AMD AMF (H.264)"),
        ("h264_videotoolbox","Apple VT H.264"),
        ("libx264",          "CPU H.264")
    ]

    for enc, name in encoders_to_test:
        try:
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "nullsrc=s=16x16:d=0.1:r=1",
                    "-c:v", enc, "-t", "0.1", "-f", "null", "-"
                ],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
            )
            print(f"✅ Using {name} ({enc})")
            return enc, name
        except Exception:
            continue

    # Fallback – should never hit this because libx264 is last in list
    return "libx264", "CPU H.264"

GPU_ENCODER, ENCODER_NAME = detect_gpu_encoder()

# --------------------------------------------------------------------------- #
#  Folder pickers – exposed to JS
@eel.expose
def choose_source():
    root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
    folder = filedialog.askdirectory(title="Select source folder with videos")
    root.destroy()
    if not folder:
        return None

    def size_human(b): return f"{math.ceil(b/1_048_576)} MB"

    files = []
    for fn in os.listdir(folder):
        if fn.lower().endswith(VIDEO_EXT):
            fp = os.path.join(folder, fn)
            if os.path.isfile(fp):
                files.append({
                    "name": fn,
                    "path": fp.replace("\\", "/"),
                    "size": size_human(os.path.getsize(fp))
                })
    print(f"📁 Loaded {len(files)} files from {folder}")
    return {"path": folder, "files": files}

@eel.expose
def choose_destination():
    root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
    folder = filedialog.askdirectory(title="Select destination folder")
    root.destroy()
    return folder or None

# --------------------------------------------------------------------------- #
#  Helpers
def _probe_duration(p: str) -> float:
    """Return clip duration in seconds (0.0 on failure)."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", p
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        return float(out) if out and out.lower() not in {"n/a", "nan"} else 0.0
    except Exception:
        return 0.0

def _needs_reencode(videos) -> bool:
    # Simple heuristic – re-encode if extensions differ
    return len({os.path.splitext(v["path"])[1].lower() for v in videos}) > 1

def _run_ffmpeg(cmd: list[str], total_sec: float, tl_name: str):
    print("🔧 " + " ".join(cmd))
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, errors="ignore") as proc:
        for line in proc.stdout:
            if line.startswith("out_time_ms="):
                elapsed = int(line.split("=")[1]) / 1_000_000
                pct = min(elapsed / total_sec, 1.0) * 100
                eta = max(total_sec - elapsed, 0)
                eel.update_progress(float(f"{pct:.2f}"), tl_name, int(eta))
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg returned {proc.returncode}")

# --------------------------------------------------------------------------- #
#  Concat – copy mode (no re-encode)
def _export_concat(tl, out_path):
    print(f"📋 Concat-copy {tl['name']}")
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt", encoding="utf-8") as flist:
        for v in tl["videos"]:
            p = os.path.abspath(v["path"]).replace("\\", "/")
            p_escaped = p.replace("'", "'\\''")
            flist.write(f"file '{p_escaped}'\n")
        list_path = flist.name

    total = sum(_probe_duration(v["path"]) for v in tl["videos"]) or 1.0
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-c", "copy", "-avoid_negative_ts", "make_zero",
        "-progress", "pipe:1", "-y", out_path
    ]
    try:
        _run_ffmpeg(cmd, total, tl["name"])
    finally:
        os.remove(list_path)

# --------------------------------------------------------------------------- #
#  Re-encode (GPU-accelerated if available)
def _export_reencode(tl, out_path):
    print(f"🎮 Re-encoding {tl['name']} with {GPU_ENCODER}")
    inputs, filt = [], []
    for idx, v in enumerate(tl["videos"]):
        inputs += ["-i", v["path"]]
        filt.append(f"[{idx}:v]")
    filter_complex = "".join(filt) + f"concat=n={len(tl['videos'])}:v=1:a=1[outv][outa]"

    total = sum(_probe_duration(v["path"]) for v in tl["videos"]) or 1.0
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", *inputs,
           "-filter_complex", filter_complex, "-map", "[outv]", "-map", "[outa]",
           "-c:v", GPU_ENCODER]

    # Quality / speed presets
    if GPU_ENCODER.startswith("libaom"):
        cmd += ["-cpu-used", "4", "-crf", "30"]
    elif "nvenc" in GPU_ENCODER or "amf" in GPU_ENCODER or "qsv" in GPU_ENCODER:
        cmd += ["-preset", "p4", "-rc", "vbr", "-b:v", "8M", "-maxrate", "12M"]
    else:  # libx264 fallback
        cmd += ["-preset", "fast", "-crf", "23"]

    cmd += ["-c:a", "aac", "-b:a", "128k", "-progress", "pipe:1", "-y", out_path]
    _run_ffmpeg(cmd, total, tl["name"])

# --------------------------------------------------------------------------- #
#  Main export entry-point
@eel.expose
def export_timelines(timelines_json: str, output_dir: str):
    timelines = json.loads(timelines_json)
    if not timelines or not output_dir:
        return "Nothing to export."

    print(f"🚀 Starting export with {ENCODER_NAME}")

    # Verify sources exist before starting
    missing = [f"{v['name']} ({v['path']})"
               for tl in timelines for v in tl["videos"]
               if not os.path.exists(v["path"])]
    if missing:
        print("❌ Missing files:\n" + "\n".join(missing))
        return f"Export failed – {len(missing)} file(s) not found."

    for tl in timelines:
        if not tl["videos"]:
            continue
        eel.start_timeline(tl["name"])

        out_path = os.path.join(output_dir, f"{tl['name'].replace(os.sep,'_').strip()}.mkv")
        try:
            if _needs_reencode(tl["videos"]):
                _export_reencode(tl, out_path)
            else:
                _export_concat(tl, out_path)
            eel.update_progress(100.0, tl["name"], 0)
        except Exception as e:
            print(f"❌ {tl['name']} failed: {e}")

    return f"Export complete – files saved to {output_dir}"

# --------------------------------------------------------------------------- #
#  System info for the UI
@eel.expose
def get_system_info():
    return {
        "encoder": GPU_ENCODER,
        "encoder_name": ENCODER_NAME,
        "gpu_acceleration": GPU_ENCODER not in {"libx264", "libaom-av1"}
    }

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    print("🎬 Video Timeline Editor")
    print(f"🖥️ Encoder → {ENCODER_NAME} ({GPU_ENCODER})")
    eel.start("index.html", size=(1380, 900),
              mode="chrome" if os.name == "nt" else None)
