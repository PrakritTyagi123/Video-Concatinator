import os, json, math, time, subprocess, tempfile, tkinter as tk, warnings
from tkinter import filedialog
import eel

# Silence the pkg_resources deprecation splash from Eel
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

# Allow CSS to be served
eel.init('web', allowed_extensions=['.js', '.html', '.css'])

VIDEO_EXT = ('.mp4', '.mov', '.mkv', '.avi', '.flv', '.webm')

# ---------- folder pickers ------------------------------------------------- #
@eel.expose
def choose_source():
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    folder = filedialog.askdirectory(title='Select source folder with videos')
    root.destroy()
    if not folder:
        return None

    def size_human(b): return f"{math.ceil(b / 1_048_576)} MB"
    files = [
        {
            "name": fn,
            "path": os.path.join(folder, fn),
            "size": size_human(os.path.getsize(os.path.join(folder, fn)))
        }
        for fn in os.listdir(folder)
        if fn.lower().endswith(VIDEO_EXT)
    ]
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

# ---------- export with live progress ------------------------------------- #
@eel.expose
def export_timelines(timelines_json: str, output_dir: str):
    timelines = json.loads(timelines_json)
    if not timelines or not output_dir:
        return "Nothing to export."

    for tl in timelines:
        if not tl["videos"]:
            continue

        # tell front‑end a new timeline is starting
        eel.start_timeline(tl["name"])

        # concat list file
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as fl:
            for v in tl["videos"]:
                fl.write(f"file '{v['path']}'\n")
            list_path = fl.name

        # duration
        durations = [_probe_duration(v["path"]) for v in tl["videos"]]
        total_sec = sum(durations)
        if total_sec < 1.0:       # guard against divide‑by‑zero
            total_sec = 1.0

        # output
        safe_name = tl["name"].replace(os.sep, "_").strip()
        out_path  = os.path.join(output_dir, f"{safe_name}.mp4")

        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error",
               "-f", "concat", "-safe", "0", "-i", list_path,
               "-c", "copy",
               "-progress", "pipe:1",
               out_path]

        with subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True) as proc:
            for line in proc.stdout:
                if line.startswith("out_time_ms="):
                    elapsed = int(line.split('=')[1]) / 1_000_000
                    pct  = min(elapsed / total_sec, 1.0) * 100
                    eta  = max(total_sec - elapsed, 0)
                    eel.update_progress(float(f"{pct:.2f}"), tl["name"], int(eta))

        # snap to 100 % for this timeline
        eel.update_progress(100.0, tl["name"], 0)
        os.remove(list_path)

    return f"Exported {len(timelines)} timeline(s) to {output_dir}"

# ---------- launch -------------------------------------------------------- #
if __name__ == "__main__":
    eel.start('index.html', size=(1380, 900),
              mode='chrome' if os.name == "nt" else None)
