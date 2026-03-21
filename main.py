#!/usr/bin/env python3
"""
Video Timeline Editor v2.1
Features:
  - GPU encoder auto-detection (NVENC, QSV, AMF, VT, CPU fallback)
  - Parallel thumbnail extraction (threaded)
  - Background probing (doesn't freeze UI)
  - Lossless concat for same-codec, re-encode only when needed
  - Wall-clock ETA, per-timeline error reporting
  - Fixed: audio streams in filter, codec-based reencode, safe filenames
"""

import os, json, math, subprocess, tempfile, time, tkinter as tk, warnings, re, hashlib, base64
from tkinter import filedialog
from concurrent.futures import ThreadPoolExecutor, as_completed
import eel

warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")
eel.init("web", allowed_extensions=[".js", ".html", ".css", ".jpg", ".jpeg", ".png", ".wav", ".mp3"])

VIDEO_EXT = (".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm", ".ts", ".m4v")
UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*]')
THUMB_DIR = os.path.join(os.path.expanduser("~"), ".videotimeline", "thumbs")
os.makedirs(THUMB_DIR, exist_ok=True)

# ─── GPU / Codec Detection ───────────────────────────────────────────────────

def detect_gpu_encoder() -> tuple[str, str]:
    encoders = [
        ("av1_nvenc","NVIDIA AV1"),("av1_qsv","Intel QSV AV1"),("av1_amf","AMD AV1"),
        ("av1_videotoolbox","Apple VT AV1"),("libaom-av1","CPU AV1"),
        ("h264_nvenc","NVIDIA NVENC (H.264)"),("h264_amf","AMD AMF (H.264)"),
        ("h264_videotoolbox","Apple VT H.264"),("libx264","CPU H.264"),
    ]
    for enc, name in encoders:
        try:
            r = subprocess.run(
                ["ffmpeg","-hide_banner","-loglevel","error",
                 "-f","lavfi","-i","nullsrc=s=256x256:d=0.1:r=1",
                 "-c:v",enc,"-t","0.1","-f","null","-"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            if r.returncode == 0:
                print(f"✅ Encoder: {name} ({enc})")
                return enc, name
        except Exception:
            continue
    return "libx264", "CPU H.264"

GPU_ENCODER, ENCODER_NAME = detect_gpu_encoder()

# ─── Probing ─────────────────────────────────────────────────────────────────

def _probe_duration(path):
    try:
        out = subprocess.check_output(
            ["ffprobe","-v","error","-select_streams","v:0",
             "-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",path],
            text=True, timeout=10).strip()
        return float(out) if out and out.lower() not in {"n/a","nan"} else 0.0
    except Exception: return 0.0

def _probe_codec(path):
    try:
        return subprocess.check_output(
            ["ffprobe","-v","error","-select_streams","v:0",
             "-show_entries","stream=codec_name","-of","default=noprint_wrappers=1:nokey=1",path],
            text=True, timeout=10).strip()
    except Exception: return ""

def _probe_resolution(path):
    try:
        return subprocess.check_output(
            ["ffprobe","-v","error","-select_streams","v:0",
             "-show_entries","stream=width,height","-of","csv=p=0:s=x",path],
            text=True, timeout=10).strip()
    except Exception: return ""

def _fmt_dur(s):
    if s <= 0: return "0:00"
    m, sec = divmod(int(s), 60); h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def _fmt_size(b):
    if b < 1_048_576: return f"{b/1024:.0f} KB"
    if b < 1_073_741_824: return f"{b/1_048_576:.0f} MB"
    return f"{b/1_073_741_824:.1f} GB"

def _safe_fn(n): return UNSAFE_CHARS.sub("_", n).strip()

# ─── Thumbnail (single file) ─────────────────────────────────────────────────

def _extract_thumb(video_path):
    h = hashlib.md5(video_path.encode()).hexdigest()[:12]
    tp = os.path.join(THUMB_DIR, f"{h}.jpg")
    if os.path.exists(tp) and os.path.getsize(tp) > 100:
        with open(tp,"rb") as f: return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
    try:
        dur = _probe_duration(video_path)
        seek = min(max(dur*0.1, 0.5), 5.0) if dur > 0 else 1.0
        subprocess.run(
            ["ffmpeg","-hide_banner","-loglevel","error","-ss",str(seek),
             "-i",video_path,"-vframes","1","-vf","scale=160:-1","-q:v","5","-y",tp],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if os.path.exists(tp) and os.path.getsize(tp) > 100:
            with open(tp,"rb") as f: return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
    except Exception as e:
        print(f"⚠️ Thumb: {os.path.basename(video_path)}: {e}")
    return None

# ─── Probe single file (for parallel use) ────────────────────────────────────

def _probe_file(fp):
    """Probe one video file completely. Returns dict. Thread-safe."""
    fn = os.path.basename(fp)
    dur = _probe_duration(fp)
    codec = _probe_codec(fp)
    res = _probe_resolution(fp)
    thumb = _extract_thumb(fp)
    return {
        "name": fn,
        "path": fp.replace("\\", "/"),
        "size": _fmt_size(os.path.getsize(fp)),
        "duration": dur,
        "durationText": _fmt_dur(dur),
        "codec": codec,
        "resolution": res,
        "thumbnail": thumb,
    }

# ─── Folder Pickers ──────────────────────────────────────────────────────────

@eel.expose
def choose_source():
    root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
    folder = filedialog.askdirectory(title="Select source folder with videos")
    root.destroy()
    if not folder: return None

    paths = sorted([
        os.path.join(folder, fn)
        for fn in os.listdir(folder)
        if fn.lower().endswith(VIDEO_EXT) and os.path.isfile(os.path.join(folder, fn))
    ])

    if not paths:
        return {"path": folder, "files": []}

    # Send file count immediately so UI can show loading state
    eel.source_loading(len(paths))

    # Parallel probe + thumbnail extraction (4 workers)
    files = [None] * len(paths)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_probe_file, p): i for i, p in enumerate(paths)}
        done = 0
        for future in as_completed(futures):
            idx = futures[future]
            try:
                files[idx] = future.result()
            except Exception as e:
                fn = os.path.basename(paths[idx])
                files[idx] = {"name": fn, "path": paths[idx].replace("\\","/"),
                              "size":"?", "duration":0, "durationText":"?",
                              "codec":"?", "resolution":"?", "thumbnail": None}
                print(f"⚠️ Probe failed: {fn}: {e}")
            done += 1
            # Stream progress to frontend
            eel.source_progress(done, len(paths), files[idx]["name"])

    print(f"📁 Loaded {len(files)} files from {folder}")
    return {"path": folder, "files": files}

@eel.expose
def choose_destination():
    root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
    folder = filedialog.askdirectory(title="Select destination folder")
    root.destroy()
    return folder or None

# ─── FFmpeg runner ───────────────────────────────────────────────────────────

def _run_ffmpeg(cmd, total_sec, tl_name):
    print("🔧 " + " ".join(cmd))
    start = time.monotonic()
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, errors="replace") as proc:
        for line in proc.stdout:
            if line.startswith("out_time_ms="):
                try: elapsed = int(line.split("=")[1].strip()) / 1_000_000
                except ValueError: continue
                pct = min(elapsed / max(total_sec, 0.01), 1.0) * 100
                wall = time.monotonic() - start
                frac = max(pct / 100, 0.001)
                eta = max((wall / frac) - wall, 0)
                eel.update_progress(round(pct, 2), tl_name, int(eta))
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg error ({proc.returncode}): {proc.stderr.read()[:500]}")

# ─── Re-encode detection ─────────────────────────────────────────────────────

def _needs_reencode(videos):
    codecs, ress = set(), set()
    for v in videos:
        c = _probe_codec(v["path"]); r = _probe_resolution(v["path"])
        if c: codecs.add(c)
        if r: ress.add(r)
    return len(codecs) > 1 or len(ress) > 1

# ─── Export: lossless concat ─────────────────────────────────────────────────

def _export_concat(tl, out_path):
    print(f"📋 Lossless concat: {tl['name']}")
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt", encoding="utf-8") as f:
        for v in tl["videos"]:
            p = os.path.abspath(v["path"]).replace("\\","/").replace("'","'\\''")
            f.write(f"file '{p}'\n")
        lp = f.name
    total = sum(_probe_duration(v["path"]) for v in tl["videos"]) or 1.0
    try:
        _run_ffmpeg(["ffmpeg","-hide_banner","-loglevel","warning",
                     "-f","concat","-safe","0","-i",lp,
                     "-c","copy","-avoid_negative_ts","make_zero",
                     "-progress","pipe:1","-y",out_path], total, tl["name"])
    finally: os.remove(lp)

# ─── Export: re-encode ───────────────────────────────────────────────────────

def _export_reencode(tl, out_path, encoder, quality):
    print(f"🎮 Re-encode: {tl['name']} → {encoder}")
    inputs, filt = [], []
    for i, v in enumerate(tl["videos"]):
        inputs += ["-i", v["path"]]
        filt.append(f"[{i}:v][{i}:a]")
    fc = "".join(filt) + f"concat=n={len(tl['videos'])}:v=1:a=1[outv][outa]"
    total = sum(_probe_duration(v["path"]) for v in tl["videos"]) or 1.0
    cmd = ["ffmpeg","-hide_banner","-loglevel","error",*inputs,
           "-filter_complex",fc,"-map","[outv]","-map","[outa]","-c:v",encoder]
    crf = {"high":23,"medium":28,"fast":32}.get(quality,23)
    if encoder.startswith("libaom"): cmd += ["-cpu-used","4","-crf",str(crf)]
    elif any(x in encoder for x in ("nvenc","amf","qsv")):
        cmd += ["-preset","p4","-rc","vbr","-b:v","8M","-maxrate","12M"]
    else:
        sp = {"high":"medium","medium":"fast","fast":"ultrafast"}.get(quality,"fast")
        cmd += ["-preset",sp,"-crf",str(crf)]
    cmd += ["-c:a","aac","-b:a","128k","-progress","pipe:1","-y",out_path]
    _run_ffmpeg(cmd, total, tl["name"])

# ─── Main export ─────────────────────────────────────────────────────────────

@eel.expose
def export_timelines(timelines_json, output_dir, fmt="mkv", quality="high"):
    tls = json.loads(timelines_json)
    if not tls or not output_dir: return {"ok":False,"msg":"Nothing to export."}
    missing = [v["name"] for t in tls for v in t["videos"] if not os.path.exists(v["path"])]
    if missing: return {"ok":False,"msg":f"{len(missing)} file(s) not found"}
    ext = {"mp4":".mp4","webm":".webm"}.get(fmt,".mkv")
    results = []
    for tl in tls:
        if not tl["videos"]: continue
        eel.start_timeline(tl["name"])
        op = os.path.join(output_dir, _safe_fn(tl["name"]) + ext)
        try:
            (_export_reencode if _needs_reencode(tl["videos"]) else _export_concat)(
                tl, op, GPU_ENCODER, quality) if _needs_reencode(tl["videos"]) else _export_concat(tl, op)
            eel.update_progress(100.0, tl["name"], 0)
            sz = os.path.getsize(op) if os.path.exists(op) else 0
            results.append({"name":tl["name"],"ok":True,"size":_fmt_size(sz)})
        except Exception as e:
            print(f"❌ {tl['name']}: {e}")
            eel.timeline_error(tl["name"], str(e))
            results.append({"name":tl["name"],"ok":False,"error":str(e)})
    ok = sum(1 for r in results if r["ok"])
    return {"ok":ok==len(results),"msg":f"Exported {ok}/{len(results)} timeline(s)","results":results}

@eel.expose
def get_system_info():
    return {"encoder":GPU_ENCODER,"encoder_name":ENCODER_NAME,
            "gpu_acceleration":GPU_ENCODER not in {"libx264","libaom-av1"}}

# ─── Entry ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🎬 Video Timeline Editor v2.1")
    print(f"🖥️  Encoder → {ENCODER_NAME} ({GPU_ENCODER})")
    eel.start("index.html", size=(1400, 900), mode="chrome" if os.name == "nt" else None)
