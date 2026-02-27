import os
import shlex
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
import sys
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_AVAILABLE = True
    BaseTk = TkinterDnD.Tk
except Exception:
    DND_AVAILABLE = False
    BaseTk = tk.Tk


def _parse_time_to_seconds(value):
    value = value.strip()
    if not value:
        return None
    parts = value.split(":")
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h = 0
        m, s = parts
    else:
        return float(value)
    return float(h) * 3600 + float(m) * 60 + float(s)


def _format_seconds(seconds):
    if seconds is None:
        return "--:--"
    seconds = max(0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _get_duration_seconds(path):
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except Exception:
        return None
    try:
        return float(proc.stdout.strip())
    except Exception:
        return None


def _get_ffmpeg_encoders():
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except Exception:
        return set()

    encoders = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("--") or line.startswith("Encoders"):
            continue
        if len(line) < 6:
            continue
        # Format: " V..... libx264 ..."
        parts = line.split()
        if len(parts) >= 2:
            encoders.add(parts[1])
    return encoders


def _get_ffmpeg_decoders():
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-decoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except Exception:
        return set()

    decoders = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("--") or line.startswith("Decoders"):
            continue
        if len(line) < 6:
            continue
        parts = line.split()
        if len(parts) >= 2:
            decoders.add(parts[1])
    return decoders


def _get_video_codec(path):
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except Exception:
        return None
    codec = proc.stdout.strip()
    return codec or None


def _pick_video_encoder(out_fmt, encoders):
    if out_fmt in {"mp4", "mov", "mkv"}:
        for cand in [
            "libx264",
            "libopenh264",
            "h264_v4l2m2m",
            "h264_vaapi",
            "h264_nvenc",
            "mpeg4",
        ]:
            if cand in encoders:
                return cand
    if out_fmt == "webm":
        for cand in ["libvpx-vp9", "libvpx", "vp9", "vp8"]:
            if cand in encoders:
                return cand
    if out_fmt == "gif":
        return "gif"
    return None


def _pick_audio_encoder(out_fmt, encoders):
    if out_fmt in {"mp4", "mov", "mkv"}:
        for cand in ["aac", "libfdk_aac"]:
            if cand in encoders:
                return cand
    if out_fmt == "webm":
        for cand in ["libopus", "libvorbis", "opus", "vorbis"]:
            if cand in encoders:
                return cand
    return None


def run_ffmpeg(cmd, on_line=None):
    if on_line:
        on_line(f"\n$ {' '.join(shlex.quote(c) for c in cmd)}\n")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in process.stdout:
        if on_line:
            on_line(line)
    process.wait()
    return process.returncode


def _native_pick_files(multiple=False):
    if sys.platform.startswith("linux"):
        if shutil.which("zenity"):
            cmd = ["zenity", "--file-selection"]
            if multiple:
                cmd += ["--multiple", "--separator=|"]
            cmd += [
                "--file-filter=Videos | *.mp4 *.mkv *.mov *.webm *.avi *.m4v *.mpg *.mpeg *.gif",
                "--file-filter=All files | *",
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if proc.returncode == 0:
                out = proc.stdout.strip()
                if not out:
                    return []
                return out.split("|") if multiple else [out]
        if shutil.which("kdialog"):
            if multiple:
                cmd = ["kdialog", "--getopenfilename", os.path.expanduser("~"), "--multiple", "--separate-output"]
            else:
                cmd = ["kdialog", "--getopenfilename", os.path.expanduser("~")]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if proc.returncode == 0:
                out = proc.stdout.strip()
                if not out:
                    return []
                return out.splitlines() if multiple else [out]
    return None


def _native_pick_dir():
    if sys.platform.startswith("linux"):
        if shutil.which("zenity"):
            cmd = ["zenity", "--file-selection", "--directory"]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if proc.returncode == 0:
                out = proc.stdout.strip()
                return out or None
        if shutil.which("kdialog"):
            cmd = ["kdialog", "--getexistingdirectory", os.path.expanduser("~")]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if proc.returncode == 0:
                out = proc.stdout.strip()
                return out or None
    return None


def build_command(values, in_path, out_path, encoders, decoders):
    out_fmt = values["format"].strip()
    fps = values["fps"].strip()
    trim_enabled = values["trim_enabled"]
    fps_enabled = values["fps_enabled"]

    if not os.path.isfile(in_path):
        raise ValueError("Input file does not exist.")
    if not out_fmt:
        raise ValueError("Output format is required.")

    cmd = ["ffmpeg", "-y"]

    if trim_enabled:
        start = values["trim_start"]
        end = values["trim_end"]
        if start is None:
            raise ValueError("Trim start time is required when Trim is enabled.")
        cmd += ["-ss", f"{start:.3f}"]
        cmd += ["-i", in_path]
        if end is not None and end > start:
            cmd += ["-to", f"{end:.3f}"]
    else:
        cmd += ["-i", in_path]

    filters = []
    if fps_enabled:
        if not fps:
            raise ValueError("Target FPS is required when FPS change is enabled.")
        try:
            float(fps)
        except ValueError:
            raise ValueError("Target FPS must be a number.")
        filters.append(f"fps={fps}")

    codec = _get_video_codec(in_path)
    needs_decode = bool(filters) or trim_enabled or out_fmt == "gif"
    if codec and needs_decode and codec not in decoders:
        raise ValueError(
            f"Your FFmpeg build cannot decode '{codec}'. Install a full FFmpeg build or disable trim/FPS change."
        )

    if out_fmt == "gif":
        gif_fps = fps if fps_enabled else "10"
        gif_filters = [f"fps={gif_fps}", "scale=640:-1:flags=lanczos"]
        cmd += ["-vf", ",".join(gif_filters), "-an"]
    else:
        if not filters and not trim_enabled and out_fmt in {"mp4", "mov", "mkv"}:
            cmd += ["-c", "copy"]
        else:
            if filters:
                cmd += ["-filter:v", ",".join(filters)]

            v_encoder = _pick_video_encoder(out_fmt, encoders)
            a_encoder = _pick_audio_encoder(out_fmt, encoders)
            if v_encoder:
                cmd += ["-c:v", v_encoder]
            if a_encoder:
                cmd += ["-c:a", a_encoder]
        if out_fmt in {"mp4", "mov"}:
            cmd += ["-movflags", "+faststart"]

    cmd.append(out_path)
    return cmd


class App(BaseTk):
    def __init__(self):
        super().__init__()
        self.title("FFmpeg GUI")
        self.geometry("940x720")
        self.minsize(860, 640)

        self.encoders = _get_ffmpeg_encoders()
        self.decoders = _get_ffmpeg_decoders()
        self.input_path = tk.StringVar()
        self.input_list = []
        self.output_dir = tk.StringVar()
        self.output_name = tk.StringVar(value="output")
        self.format_var = tk.StringVar(value="mp4")
        self.fps_var = tk.StringVar()
        self.trim_enabled = tk.BooleanVar(value=False)
        self.trim_start_sec = tk.DoubleVar(value=0.0)
        self.trim_end_sec = tk.DoubleVar(value=0.0)
        self.trim_start_label = tk.StringVar(value="00:00")
        self.trim_end_label = tk.StringVar(value="00:00")
        self.duration_label = tk.StringVar(value="Duration: --:--")
        self.preview_time = tk.DoubleVar(value=0.0)
        self.preview_label = tk.StringVar(value="Preview: 00:00")
        self.preview_job = None
        self.preview_image = None
        self.preview_cache = {}
        self.preview_cache_order = []
        self.fps_enabled = tk.BooleanVar(value=False)
        self.keep_names = tk.BooleanVar(value=True)
        self.preset_var = tk.StringVar(value="Custom")
        self.sort_var = tk.StringVar(value="Name A-Z")

        self.total_duration = None
        self._build_ui()

    def _build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Section.TLabelframe", padding=(12, 10))
        style.configure("TButton", padding=(10, 6))

        canvas = tk.Canvas(self, highlightthickness=0)
        vscroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        container = ttk.Frame(canvas, padding=16)
        container_id = canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_container_config(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_config(event):
            canvas.itemconfigure(container_id, width=event.width)

        container.bind("<Configure>", _on_container_config)
        canvas.bind("<Configure>", _on_canvas_config)

        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-3, "units")
            elif event.num == 5:
                canvas.yview_scroll(3, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

        ttk.Label(container, text="FFmpeg Video Tools", style="Header.TLabel").pack(
            anchor="w", pady=(0, 12)
        )

        io_frame = ttk.LabelFrame(container, text="Files", style="Section.TLabelframe")
        io_frame.pack(fill="x", pady=8)

        ttk.Label(io_frame, text="Input file").pack(anchor="w")
        in_row = ttk.Frame(io_frame)
        in_row.pack(fill="x", pady=6)
        ttk.Entry(in_row, textvariable=self.input_path).pack(side="left", fill="x", expand=True)
        ttk.Button(in_row, text="Browse", command=self._pick_input).pack(side="left", padx=6)
        ttk.Button(in_row, text="Add to batch", command=self._add_to_batch).pack(side="left")

        ttk.Label(io_frame, text="Batch list (optional)").pack(anchor="w", pady=(8, 0))
        list_row = ttk.Frame(io_frame)
        list_row.pack(fill="x", pady=6)
        self.batch_list = tk.Listbox(list_row, height=5)
        self.batch_list.pack(side="left", fill="both", expand=True)
        list_btns = ttk.Frame(list_row)
        list_btns.pack(side="left", padx=8)
        ttk.Button(list_btns, text="Remove", command=self._remove_selected).pack(fill="x", pady=2)
        ttk.Button(list_btns, text="Clear", command=self._clear_batch).pack(fill="x", pady=2)

        if DND_AVAILABLE:
            self.batch_list.drop_target_register(DND_FILES)
            self.batch_list.dnd_bind("<<Drop>>", self._on_drop_files)

        sort_row = ttk.Frame(io_frame)
        sort_row.pack(fill="x", pady=(2, 6))
        ttk.Label(sort_row, text="Sort batch").pack(side="left")
        ttk.Combobox(
            sort_row,
            textvariable=self.sort_var,
            values=[
                "Name A-Z",
                "Name Z-A",
                "Date Newest",
                "Date Oldest",
                "Size Largest",
                "Size Smallest",
            ],
            width=14,
            state="readonly",
        ).pack(side="left", padx=6)
        ttk.Button(sort_row, text="Sort", command=self._sort_batch).pack(side="left")

        ttk.Label(io_frame, text="Output folder").pack(anchor="w")
        out_row = ttk.Frame(io_frame)
        out_row.pack(fill="x", pady=6)
        ttk.Entry(out_row, textvariable=self.output_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(out_row, text="Browse", command=self._pick_output).pack(side="left", padx=6)

        name_row = ttk.Frame(io_frame)
        name_row.pack(fill="x", pady=(4, 2))
        ttk.Label(name_row, text="Output name").pack(side="left")
        ttk.Entry(name_row, textvariable=self.output_name, width=24).pack(side="left", padx=6)
        ttk.Checkbutton(
            name_row, text="Keep original names for batch", variable=self.keep_names
        ).pack(side="left", padx=6)

        fmt_row = ttk.Frame(io_frame)
        fmt_row.pack(fill="x", pady=(2, 0))
        ttk.Label(fmt_row, text="Format").pack(side="left")
        ttk.Combobox(
            fmt_row,
            textvariable=self.format_var,
            values=["mp4", "mkv", "mov", "webm", "gif"],
            width=8,
            state="readonly",
        ).pack(side="left", padx=6)

        preset_frame = ttk.LabelFrame(container, text="Presets", style="Section.TLabelframe")
        preset_frame.pack(fill="x", pady=8)
        preset_row = ttk.Frame(preset_frame)
        preset_row.pack(fill="x")
        ttk.Combobox(
            preset_row,
            textvariable=self.preset_var,
            values=["Custom", "MP4 60fps", "MP4 30fps", "WebM 30fps", "GIF 10fps"],
            state="readonly",
            width=14,
        ).pack(side="left")
        ttk.Button(preset_row, text="Apply Preset", command=self._apply_preset).pack(
            side="left", padx=8
        )

        options_frame = ttk.LabelFrame(container, text="Options", style="Section.TLabelframe")
        options_frame.pack(fill="x", pady=8)

        fps_row = ttk.Frame(options_frame)
        fps_row.pack(fill="x", pady=4)
        ttk.Checkbutton(fps_row, text="Change FPS", variable=self.fps_enabled).pack(side="left")
        ttk.Label(fps_row, text="Target").pack(side="left", padx=(12, 4))
        ttk.Entry(fps_row, textvariable=self.fps_var, width=8).pack(side="left")

        trim_row = ttk.Frame(options_frame)
        trim_row.pack(fill="x", pady=4)
        ttk.Checkbutton(trim_row, text="Trim clip", variable=self.trim_enabled).pack(side="left")
        ttk.Label(trim_row, textvariable=self.duration_label).pack(side="left", padx=(12, 0))

        trim_sliders = ttk.Frame(options_frame)
        trim_sliders.pack(fill="x", pady=4)

        start_row = ttk.Frame(trim_sliders)
        start_row.pack(fill="x", pady=2)
        ttk.Label(start_row, text="Start").pack(side="left", padx=(0, 6))
        self.start_scale = ttk.Scale(
            start_row,
            from_=0.0,
            to=1.0,
            variable=self.trim_start_sec,
            command=lambda _: self._sync_trim_labels(),
        )
        self.start_scale.pack(side="left", fill="x", expand=True)
        ttk.Label(start_row, textvariable=self.trim_start_label, width=8).pack(side="left", padx=6)

        end_row = ttk.Frame(trim_sliders)
        end_row.pack(fill="x", pady=2)
        ttk.Label(end_row, text="End").pack(side="left", padx=(0, 12))
        self.end_scale = ttk.Scale(
            end_row,
            from_=0.0,
            to=1.0,
            variable=self.trim_end_sec,
            command=lambda _: self._sync_trim_labels(),
        )
        self.end_scale.pack(side="left", fill="x", expand=True)
        ttk.Label(end_row, textvariable=self.trim_end_label, width=8).pack(side="left", padx=6)

        preview_frame = ttk.LabelFrame(container, text="Preview", style="Section.TLabelframe")
        preview_frame.pack(fill="x", pady=8)
        preview_row = ttk.Frame(preview_frame)
        preview_row.pack(fill="x")
        ttk.Label(preview_row, textvariable=self.preview_label).pack(side="left")
        self.preview_scale = ttk.Scale(
            preview_row,
            from_=0.0,
            to=1.0,
            variable=self.preview_time,
            command=lambda _: self._schedule_preview(),
        )
        self.preview_scale.pack(side="left", fill="x", expand=True, padx=8)
        self.preview_img_label = ttk.Label(preview_frame)
        self.preview_img_label.pack(pady=6)

        action_frame = ttk.Frame(container)
        action_frame.pack(fill="x", pady=8)
        ttk.Button(action_frame, text="Run", command=self._run).pack(side="left")
        ttk.Button(action_frame, text="Clear Log", command=self._clear_log).pack(side="left", padx=6)
        ttk.Button(action_frame, text="Copy Log", command=self._copy_log).pack(side="left")
        self.progress = ttk.Progressbar(action_frame, length=260, mode="determinate")
        self.progress.pack(side="left", padx=10)

        log_frame = ttk.LabelFrame(container, text="Log", style="Section.TLabelframe")
        log_frame.pack(fill="both", expand=True, pady=8)

        log_inner = ttk.Frame(log_frame)
        log_inner.pack(fill="both", expand=True)
        self.log = tk.Text(log_inner, height=14, wrap="word")
        self.log.pack(side="left", fill="both", expand=True)
        log_scroll = ttk.Scrollbar(log_inner, orient="vertical", command=self.log.yview)
        log_scroll.pack(side="left", fill="y")
        self.log.configure(yscrollcommand=log_scroll.set)
        self.log.bind("<Key>", lambda _: "break")


    def _pick_input(self):
        native = _native_pick_files(multiple=False)
        if native is None:
            native = [
                filedialog.askopenfilename(
                    filetypes=[
                        ("Videos", "*.mp4 *.mkv *.mov *.webm *.avi *.m4v *.mpg *.mpeg *.gif"),
                        ("All files", "*.*"),
                    ]
                )
            ]
        if native and native[0]:
            path = native[0]
            self.input_path.set(path)
            self._load_duration(path)
            self._schedule_preview(force=True)

    def _add_to_batch(self):
        native = _native_pick_files(multiple=True)
        if native is None:
            native = list(
                filedialog.askopenfilenames(
                    filetypes=[
                        ("Videos", "*.mp4 *.mkv *.mov *.webm *.avi *.m4v *.mpg *.mpeg *.gif"),
                        ("All files", "*.*"),
                    ]
                )
            )
        paths = native or []
        if not paths:
            return
        for p in paths:
            if p not in self.input_list:
                self.input_list.append(p)
                self.batch_list.insert(tk.END, p)
        if paths and not self.input_path.get():
            self.input_path.set(paths[0])
            self._load_duration(paths[0])
            self._schedule_preview(force=True)

    def _remove_selected(self):
        sel = list(self.batch_list.curselection())
        sel.reverse()
        for idx in sel:
            path = self.batch_list.get(idx)
            self.batch_list.delete(idx)
            if path in self.input_list:
                self.input_list.remove(path)

    def _clear_batch(self):
        self.batch_list.delete(0, tk.END)
        self.input_list = []

    def _sort_batch(self):
        if not self.input_list:
            return
        mode = self.sort_var.get()
        items = list(self.input_list)
        if mode in {"Name A-Z", "Name Z-A"}:
            items.sort(key=lambda p: os.path.basename(p).lower())
            if mode == "Name Z-A":
                items.reverse()
        elif mode in {"Date Newest", "Date Oldest"}:
            items.sort(key=lambda p: os.path.getmtime(p))
            if mode == "Date Newest":
                items.reverse()
        elif mode in {"Size Largest", "Size Smallest"}:
            items.sort(key=lambda p: os.path.getsize(p))
            if mode == "Size Largest":
                items.reverse()

        self.input_list = items
        self.batch_list.delete(0, tk.END)
        for p in self.input_list:
            self.batch_list.insert(tk.END, p)

    def _on_drop_files(self, event):
        paths = self._parse_drop_files(event.data)
        if not paths:
            return
        for p in paths:
            if os.path.isfile(p) and p not in self.input_list:
                self.input_list.append(p)
                self.batch_list.insert(tk.END, p)
        if not self.input_path.get() and self.input_list:
            self.input_path.set(self.input_list[0])
            self._load_duration(self.input_list[0])
            self._schedule_preview(force=True)

    def _parse_drop_files(self, data):
        if not data:
            return []
        files = []
        buf = ""
        in_brace = False
        for ch in data:
            if ch == "{":
                in_brace = True
                buf = ""
            elif ch == "}":
                in_brace = False
                if buf:
                    files.append(buf)
                    buf = ""
            elif ch == " " and not in_brace:
                if buf:
                    files.append(buf)
                    buf = ""
            else:
                buf += ch
        if buf:
            files.append(buf)
        return files

    def _pick_output(self):
        path = _native_pick_dir()
        if path is None:
            path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.configure(state="normal")

    def _copy_log(self):
        text = self.log.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_idletasks()

    def _load_duration(self, path):
        duration = _get_duration_seconds(path)
        self.total_duration = duration
        if not duration or duration <= 0:
            self.duration_label.set("Duration: --:--")
            self.start_scale.configure(from_=0.0, to=1.0)
            self.end_scale.configure(from_=0.0, to=1.0)
            self.trim_start_sec.set(0.0)
            self.trim_end_sec.set(0.0)
            self._sync_trim_labels()
            self.preview_scale.configure(from_=0.0, to=1.0)
            self.preview_time.set(0.0)
            self.preview_label.set("Preview: --:--")
            return

        self.duration_label.set(f"Duration: {_format_seconds(duration)}")
        self.start_scale.configure(from_=0.0, to=duration)
        self.end_scale.configure(from_=0.0, to=duration)
        self.preview_scale.configure(from_=0.0, to=duration)
        if self.trim_end_sec.get() <= 0.0:
            self.trim_end_sec.set(duration)
        if self.trim_start_sec.get() > duration:
            self.trim_start_sec.set(0.0)
        if self.trim_end_sec.get() > duration:
            self.trim_end_sec.set(duration)
        self._sync_trim_labels()
        self.preview_time.set(min(self.preview_time.get(), duration))
        self.preview_label.set(f"Preview: {_format_seconds(self.preview_time.get())}")

    def _sync_trim_labels(self):
        start = self.trim_start_sec.get()
        end = self.trim_end_sec.get()
        if end < start:
            end = start
            self.trim_end_sec.set(end)
        self.trim_start_label.set(_format_seconds(start))
        self.trim_end_label.set(_format_seconds(end))

    def _schedule_preview(self, force=False):
        if self.preview_job:
            self.after_cancel(self.preview_job)
        self.preview_job = self.after(200 if not force else 0, self._generate_preview)

    def _generate_preview(self):
        self.preview_job = None
        path = self.input_path.get().strip()
        if not path or not os.path.isfile(path):
            return
        t = float(self.preview_time.get())
        self.preview_label.set(f"Preview: {_format_seconds(t)}")
        codec = _get_video_codec(path)
        if codec and codec not in self.decoders:
            self.preview_img_label.configure(image="")
            self.preview_label.set("Preview: decoder missing")
            return
        key = (path, int(t * 2))
        if key in self.preview_cache:
            self._set_preview_image(self.preview_cache[key])
            return

        def worker():
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                f"{t:.3f}",
                "-i",
                path,
                "-frames:v",
                "1",
                "-vf",
                "scale=360:-1:flags=lanczos",
                "-q:v",
                "2",
                tmp_path,
            ]
            try:
                subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
                if os.path.exists(tmp_path):
                    self.after(0, self._cache_preview_image, key, tmp_path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        threading.Thread(target=worker, daemon=True).start()

    def _cache_preview_image(self, key, path):
        try:
            img = tk.PhotoImage(file=path)
            self.preview_cache[key] = img
            self.preview_cache_order.append(key)
            if len(self.preview_cache_order) > 20:
                old = self.preview_cache_order.pop(0)
                if old in self.preview_cache:
                    del self.preview_cache[old]
            self.preview_image = img
            self.preview_img_label.configure(image=img)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def _set_preview_image(self, img):
        self.preview_image = img
        self.preview_img_label.configure(image=img)

    def _apply_preset(self):
        preset = self.preset_var.get()
        if preset == "MP4 60fps":
            self.format_var.set("mp4")
            self.fps_enabled.set(True)
            self.fps_var.set("60")
        elif preset == "MP4 30fps":
            self.format_var.set("mp4")
            self.fps_enabled.set(True)
            self.fps_var.set("30")
        elif preset == "WebM 30fps":
            self.format_var.set("webm")
            self.fps_enabled.set(True)
            self.fps_var.set("30")
        elif preset == "GIF 10fps":
            self.format_var.set("gif")
            self.fps_enabled.set(True)
            self.fps_var.set("10")

    def _build_output_path(self, in_path, values):
        out_dir = values["output_dir"].strip()
        out_name = values["output_name"].strip()
        out_fmt = values["format"].strip()
        if not out_dir:
            raise ValueError("Choose an output folder.")
        if not os.path.isdir(out_dir):
            raise ValueError("Output folder does not exist.")
        if len(self.input_list) > 1 and values["keep_names"]:
            base = os.path.splitext(os.path.basename(in_path))[0]
            out_name = base
        if not out_name:
            raise ValueError("Output filename is required.")
        if not out_name.endswith(f".{out_fmt}"):
            out_name = f"{out_name}.{out_fmt}"
        return os.path.join(out_dir, out_name)

    def _queue_log(self, line):
        self.after(0, self._append_log, line)

    def _append_log(self, line):
        self.log.configure(state="normal")
        self.log.insert(tk.END, line)
        self.log.see(tk.END)
        self.log.configure(state="normal")
        self._set_progress_from_line(line)

    def _set_progress_from_line(self, line):
        if "Duration:" in line:
            try:
                dur = line.split("Duration:")[1].split(",")[0].strip()
                self.total_duration = _parse_time_to_seconds(dur)
            except Exception:
                self.total_duration = None
        if "time=" in line and self.total_duration:
            try:
                t = line.split("time=")[1].split(" ")[0].strip()
                current = _parse_time_to_seconds(t)
                if current is None:
                    return
                pct = max(0, min(100, (current / self.total_duration) * 100))
                self.progress["value"] = pct
            except Exception:
                pass

    def _set_progress(self, value):
        self.progress["value"] = value

    def _ui_message(self, kind, title, msg):
        if kind == "info":
            messagebox.showinfo(title, msg)
        else:
            messagebox.showerror(title, msg)

    def _run(self):
        values = {
            "input_path": self.input_path.get(),
            "output_dir": self.output_dir.get(),
            "output_name": self.output_name.get(),
            "format": self.format_var.get(),
            "fps": self.fps_var.get(),
            "trim_enabled": self.trim_enabled.get(),
            "trim_start": None,
            "trim_end": None,
            "fps_enabled": self.fps_enabled.get(),
            "keep_names": self.keep_names.get(),
        }

        if self.input_list:
            inputs = list(self.input_list)
        elif values["input_path"].strip():
            inputs = [values["input_path"].strip()]
        else:
            messagebox.showerror("Input error", "Choose an input file.")
            return

        def worker():
            for in_path in inputs:
                try:
                    if values["trim_enabled"]:
                        start = float(self.trim_start_sec.get())
                        end = float(self.trim_end_sec.get())
                        duration = _get_duration_seconds(in_path)
                        if duration and start >= duration:
                            raise ValueError("Trim start must be within the video duration.")
                        if duration and end >= duration - 0.01:
                            end = None
                        if end is not None and end <= start + 0.01:
                            end = None
                        values["trim_start"] = start
                        values["trim_end"] = end

                    out_path = self._build_output_path(in_path, values)
                    cmd = build_command(values, in_path, out_path, self.encoders, self.decoders)
                except ValueError as e:
                    self.after(0, self._ui_message, "error", "Input error", str(e))
                    return
                self.after(0, self._set_progress, 0)
                code = run_ffmpeg(cmd, self._queue_log)
                if code != 0:
                    self.after(
                        0,
                        self._ui_message,
                        "error",
                        "FFmpeg error",
                        "FFmpeg finished with errors. Check the log.",
                    )
                    return
            self.after(0, self._ui_message, "info", "Done", "All jobs finished.")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found on PATH. Please install ffmpeg.")

    app = App()
    app.mainloop()
