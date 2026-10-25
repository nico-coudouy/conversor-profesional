import sys
import os
import subprocess
import time
import re
import yt_dlp

from PySide6.QtCore import QThread, Signal

# ───────── RUTA PORTABLE FFMPEG ─────────
if getattr(sys, 'frozen', False):
    ffmpeg_path = os.path.join(sys._MEIPASS, "ffmpeg.exe")
    ffprobe_path = os.path.join(sys._MEIPASS, "ffprobe.exe")
else:
    ffmpeg_path = "ffmpeg"
    ffprobe_path = "ffprobe"

# ───────── PRESETS DE CALIDAD ─────────
QUALITY_PRESETS = {
    0: {"label": "Proxy", "crf": 30, "preset": "ultrafast"},
    1: {"label": "YouTube", "crf": 23, "preset": "fast"},
    2: {"label": "Alta calidad", "crf": 18, "preset": "slow"},
    3: {"label": "Liviano", "crf": 28, "preset": "veryfast"},
}

class ConvertWorker(QThread):

    progress_file = Signal(int)
    progress_global = Signal(int)
    status = Signal(str)
    finished = Signal(str, str)
    error = Signal(str, str)

    def __init__(self, files=None, youtube_link=None, convert_after_download=True,
                 output_folder="", quality_preset=1):
        super().__init__()
        self.files = files or []
        self.youtube_link = youtube_link
        self.convert_after_download = convert_after_download
        self.output_folder = output_folder or os.getcwd()
        self.quality_preset = quality_preset
        self._cancelled = False
        self.process = None

    # ───────── CANCELAR ─────────
    def cancel(self):
        self._cancelled = True
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass

    # ───────── DESCARGA ─────────
    def download_video(self, url):
        self.status.emit("⬇️ Descargando video (máxima calidad)…")
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mkv",
            "outtmpl": os.path.join(self.output_folder, "%(title)s.%(ext)s"),
            "noplaylist": True,
            "progress_hooks": [self.yt_progress_hook],
            "quiet": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        return filename

    def yt_progress_hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                percent = int(downloaded / total * 100)
                self.progress_file.emit(percent)
            eta = d.get("eta")
            if eta:
                mins, secs = divmod(eta, 60)
                self.status.emit(f"⬇️ Descargando… faltan {mins:02d}:{secs:02d}")

    # ───────── UTILIDADES ─────────
    def get_duration(self, path):
        try:
            out = subprocess.check_output(
                [ffprobe_path, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", path],
                text=True
            )
            return float(out.strip())
        except Exception:
            return None

    # ───────── CONVERSIÓN ─────────
    def convert_video(self, input_path, output_path, update_cb):
        preset = QUALITY_PRESETS[self.quality_preset]
        duration = self.get_duration(input_path)
        self.status.emit(f"🎞️ Convirtiendo ({preset['label']})")

        cmd = [
            ffmpeg_path, "-y",
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", preset["preset"],
            "-crf", str(preset["crf"]),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            output_path
        ]

        self.process = subprocess.Popen(
            cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
            text=True, errors="ignore"
        )

        start = time.time()
        for line in self.process.stderr:
            if self._cancelled:
                self.process.terminate()
                return False
            if duration:
                match = re.search(r"time=(\d+:\d+:\d+\.\d+)", line)
                if match:
                    h, m, s = match.group(1).split(":")
                    current = int(h) * 3600 + int(m) * 60 + float(s)
                    percent = min(99, int(current / duration * 100))
                    update_cb(percent)

        self.process.wait()
        update_cb(100)
        return self.process.returncode == 0

    # ───────── RUN ─────────
    def run(self):
        if self.youtube_link:
            downloaded_file = self.download_video(self.youtube_link)
            if not self.convert_after_download:
                self.finished.emit(os.path.basename(downloaded_file), downloaded_file)
                return
            self.files = [downloaded_file]

        total = len(self.files)
        progress = [0] * total
        for i, path in enumerate(self.files):
            if self._cancelled:
                return
            name = os.path.basename(path)
            output = os.path.join(self.output_folder, os.path.splitext(name)[0] + "_final.mp4")
            def update(p, idx=i):
                progress[idx] = p
                self.progress_file.emit(p)
                self.progress_global.emit(int(sum(progress) / total))
            ok = self.convert_video(path, output, update)
            if ok:
                self.finished.emit(name, output)
            else:
                self.error.emit(name, "Error de conversión")
                return
        self.status.emit("✅ Conversión finalizada")
