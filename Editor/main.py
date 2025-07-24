import os, json, math, time, subprocess, tempfile, tkinter as tk, warnings
from tkinter import filedialog
import eel

# Silence the pkg_resources deprecation splash from Eel
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

# Allow CSS to be served
eel.init('web', allowed_extensions=['.js', '.html', '.css'])

VIDEO_EXT = ('.mp4', '.mov', '.mkv', '.avi', '.flv', '.webm')

# ---------- GPU Detection -------------------------------------------------- #
def detect_gpu_encoder():
    """
    Detect available GPU encoders and return the best option.
    Priority: NVENC (NVIDIA) > AMF (AMD) > VideoToolbox (macOS) > CPU fallback
    """
    encoders_to_test = [
        ("h264_nvenc", "NVIDIA NVENC"),
        ("h264_amf", "AMD AMF"), 
        ("h264_videotoolbox", "Apple VideoToolbox"),
        ("libx264", "CPU (fallback)")
    ]
    
    for encoder, name in encoders_to_test:
        try:
            # Test if encoder is available
            result = subprocess.run([
                "ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1",
                "-c:v", encoder, "-t", "1", "-f", "null", "-"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✅ Using {name} encoder: {encoder}")
                return encoder, name
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    # Fallback to libx264 if nothing else works
    print("⚠️  Using CPU fallback encoder: libx264")
    return "libx264", "CPU (fallback)"

# Detect best encoder at startup
GPU_ENCODER, ENCODER_NAME = detect_gpu_encoder()

# ---------- folder pickers ------------------------------------------------- #
@eel.expose
def choose_source():
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    folder = filedialog.askdirectory(title='Select source folder with videos')
    root.destroy()
    if not folder:
        return None

    def size_human(b): return f"{math.ceil(b / 1_048_576)} MB"
    
    files = []
    for fn in os.listdir(folder):
        if fn.lower().endswith(VIDEO_EXT):
            full_path = os.path.join(folder, fn)
            # Verify file exists and is accessible
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    file_size = os.path.getsize(full_path)
                    files.append({
                        "name": fn,
                        "path": full_path.replace("\\", "/"),  # Use full absolute path
                        "size": size_human(file_size)
                    })
                    print(f"✅ Added: {fn} ({full_path})")
                except OSError as e:
                    print(f"❌ Error accessing {fn}: {e}")
            else:
                print(f"❌ File not accessible: {full_path}")
    
    print(f"📁 Loaded {len(files)} video files from {folder}")
    return {"path": folder, "files": files}

@eel.expose
def choose_destination():
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    folder = filedialog.askdirectory(title='Select destination folder')
    root.destroy()
    return folder or None

# ---------- duration helper ------------------------------------------------ #
def _probe_duration(path) -> float:
    """
    Robustly return clip duration in seconds.
    • 'N/A', '', or any exception -> 0.0
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
        if not out or out.lower() in {"n/a", "nan"}:
            return 0.0
        return float(out)
    except Exception:
        return 0.0

# ---------- GPU-accelerated export with live progress --------------------- #
@eel.expose
def export_timelines(timelines_json: str, output_dir: str):
    timelines = json.loads(timelines_json)
    if not timelines or not output_dir:
        return "Nothing to export."

    print(f"🚀 Starting export with {ENCODER_NAME}")
    
    # Validate all file paths before starting
    missing_files = []
    for tl in timelines:
        for video in tl["videos"]:
            if not os.path.exists(video["path"]):
                missing_files.append(f"{video['name']} ({video['path']})")
    
    if missing_files:
        error_msg = f"❌ Missing files detected:\n" + "\n".join(missing_files)
        print(error_msg)
        return f"Export failed: {len(missing_files)} files not found. Check console for details."

    for tl in timelines:
        if not tl["videos"]:
            continue

        # tell front‑end a new timeline is starting
        eel.start_timeline(tl["name"])

        # Check if we need re-encoding (mixed codecs/formats)
        needs_reencoding = _check_needs_reencoding(tl["videos"])
        
        # output
        safe_name = tl["name"].replace(os.sep, "_").strip()
        out_path = os.path.join(output_dir, f"{safe_name}.mp4")

        if needs_reencoding:
            _export_with_reencoding(tl, out_path)
        else:
            _export_with_concat(tl, out_path)

        # snap to 100% for this timeline
        eel.update_progress(100.0, tl["name"], 0)

    return f"Exported {len(timelines)} timeline(s) to {output_dir} using {ENCODER_NAME}"

def _check_needs_reencoding(videos):
    """
    Check if videos have different codecs/formats that require re-encoding.
    For simplicity, we'll re-encode if we detect mixed formats or if copy fails.
    """
    # For now, let's be conservative and re-encode when we have mixed extensions
    extensions = set(os.path.splitext(v["path"])[1].lower() for v in videos)
    return len(extensions) > 1

def _export_with_concat(tl, out_path):
    """Fast concatenation using copy (no re-encoding)"""
    print(f"📋 Concatenating {tl['name']} (copy mode)")
    
    # concat list file with proper Windows path handling
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt", encoding='utf-8') as fl:
        for v in tl["videos"]:
            # Convert to absolute path and normalize separators
            abs_path = os.path.abspath(v['path'])
            # Use forward slashes for ffmpeg compatibility and escape properly
            normalized_path = abs_path.replace('\\', '/')
            # Escape single quotes and wrap in quotes
            escaped_path = normalized_path.replace("'", "'\"'\"'")
            fl.write(f"file '{escaped_path}'\n")
        list_path = fl.name
    
    # Debug: print the concat file contents
    print(f"📄 Concat file contents:")
    with open(list_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            print(f"  {line_num}: {line.strip()}")
            # Verify file exists
            file_path = line.strip().replace("file '", "").replace("'", "")
            if not os.path.exists(file_path.replace('/', '\\')):
                print(f"  ❌ File not found: {file_path}")
            else:
                print(f"  ✅ File exists: {file_path}")

    # duration calculation
    durations = [_probe_duration(v["path"]) for v in tl["videos"]]
    total_sec = sum(durations)
    if total_sec < 1.0:
        total_sec = 1.0

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "warning",
           "-f", "concat", "-safe", "0", "-i", list_path,
           "-c", "copy",
           "-avoid_negative_ts", "make_zero",
           "-progress", "pipe:1",
           "-y", out_path]

    print(f"🔧 Running command: {' '.join(cmd)}")

    try:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
            stderr_output = []
            for line in proc.stdout:
                if line.startswith("out_time_ms="):
                    elapsed = int(line.split('=')[1]) / 1_000_000
                    pct = min(elapsed / total_sec, 1.0) * 100
                    eta = max(total_sec - elapsed, 0)
                    eel.update_progress(float(f"{pct:.2f}"), tl["name"], int(eta))
            
            # Capture any errors
            stderr_output = proc.stderr.read()
            if stderr_output:
                print(f"❌ FFmpeg stderr: {stderr_output}")
                
            if proc.returncode != 0:
                print(f"❌ FFmpeg failed with return code: {proc.returncode}")
                # Fallback to re-encoding if concat fails
                print("🔄 Falling back to re-encoding mode...")
                _export_with_reencoding(tl, out_path)
                
    except Exception as e:
        print(f"❌ Export error: {e}")
        # Fallback to re-encoding
        print("🔄 Falling back to re-encoding mode...")
        _export_with_reencoding(tl, out_path)
    finally:
        if os.path.exists(list_path):
            os.remove(list_path)

def _export_with_reencoding(tl, out_path):
    """GPU-accelerated re-encoding and concatenation"""
    print(f"🎮 Re-encoding {tl['name']} with GPU acceleration ({GPU_ENCODER})")
    
    # Create filter complex for concatenation with re-encoding
    inputs = []
    filter_parts = []
    
    for i, v in enumerate(tl["videos"]):
        inputs.extend(["-i", v["path"]])
        filter_parts.append(f"[{i}:v]")
    
    filter_complex = "".join(filter_parts) + f"concat=n={len(tl['videos'])}:v=1:a=1[outv][outa]"
    
    # duration calculation  
    durations = [_probe_duration(v["path"]) for v in tl["videos"]]
    total_sec = sum(durations)
    if total_sec < 1.0:
        total_sec = 1.0

    # Build ffmpeg command with GPU acceleration
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", GPU_ENCODER,
        "-preset", "fast" if GPU_ENCODER == "libx264" else "p4",  # GPU preset
        "-crf", "23" if GPU_ENCODER == "libx264" else "28",       # Quality setting
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-progress", "pipe:1",
        "-y", out_path
    ])

    # Add GPU-specific optimizations
    if "nvenc" in GPU_ENCODER:
        cmd.extend(["-gpu", "0", "-rc", "vbr", "-b:v", "5M", "-maxrate", "8M"])
    elif "amf" in GPU_ENCODER:
        cmd.extend(["-rc", "vbr_peak", "-b:v", "5M", "-maxrate", "8M"])
    elif "videotoolbox" in GPU_ENCODER:
        cmd.extend(["-b:v", "5M"])

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
        for line in proc.stdout:
            if line.startswith("out_time_ms="):
                elapsed = int(line.split('=')[1]) / 1_000_000
                pct = min(elapsed / total_sec, 1.0) * 100
                eta = max(total_sec - elapsed, 0)
                eel.update_progress(float(f"{pct:.2f}"), tl["name"], int(eta))

# ---------- System info ---------------------------------------------------- #
@eel.expose
def get_system_info():
    """Return system information including detected GPU encoder"""
    return {
        "encoder": GPU_ENCODER,
        "encoder_name": ENCODER_NAME,
        "gpu_acceleration": GPU_ENCODER != "libx264"
    }

# ---------- launch -------------------------------------------------------- #
if __name__ == "__main__":
    print("🎬 Video Timeline Editor")
    print(f"📱 Detected encoder: {ENCODER_NAME} ({GPU_ENCODER})")
    
    eel.start('index.html', size=(1380, 900),
              mode='chrome' if os.name == "nt" else None)