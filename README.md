# FFmpeg GUI (Tkinter)

Simple GUI for:
- increasing FPS
- changing format
- trimming clips (slider)
- thumbnail preview scrubber
- drag-and-drop batch input (optional)
- native file picker via Browse buttons (uses Zenity/KDialog on Linux if available)
- batch processing (with sorting)
- progress display
- presets

## Requirements
- Python 3.x
- ffmpeg installed and on PATH
- Optional: `tkinterdnd2` for drag-and-drop

### OS Notes
- Windows: Tkinter is bundled with standard Python installers.
- macOS: Tkinter is bundled with the official Python.org installer.
- Linux: You may need a separate package for Tkinter (often `python3-tk`).
- Linux native picker: install `zenity` (GNOME) or `kdialog` (KDE) for true native dialogs.

Install drag-and-drop support:
```bash
pip install tkinterdnd2
```

## Windows & macOS
This app is cross‑platform. Run it the same way on Windows or macOS:

Windows (PowerShell):
```powershell
python app.py
```

macOS (Terminal):
```bash
python3 app.py
```

## Run
```bash
python3 app.py
```

## Notes
- The app auto-selects a compatible video/audio encoder based on your local ffmpeg build.
- If `libx264` is not available, it will fall back to another encoder or let ffmpeg pick defaults.
- If your FFmpeg build lacks a decoder (e.g., HEVC), trim/FPS changes will fail until you install a full FFmpeg build.
- For `gif`, it uses a simple `fps=10,scale=640:-1` preset and removes audio.
# FFmpeg-GUI-
# FFmpeg-GUI-
# FFmpeg-GUI-
# FFmpeg-GUI-
