# FFmpeg GUI

A user-friendly graphical interface for FFmpeg video processing built with Python and Tkinter.

## Features

- **Format Conversion**: Convert videos between MP4, MKV, MOV, WebM, and GIF formats
- **Batch Processing**: Process multiple videos at once with automatic naming
- **Video Trimming**: Trim videos with visual sliders showing start/end times
- **FPS Control**: Change frame rate of videos
- **Preview System**: Generate thumbnails at any point in the video with caching
- **Drag & Drop**: Drop video files directly into the batch list (requires tkinterdnd2)
- **Presets**: Quick apply common settings (MP4 60fps, MP4 30fps, WebM 30fps, GIF 10fps)
- **Batch Sorting**: Sort files by name, date, or size
- **Real-time Progress**: Monitor FFmpeg output and progress bar
- **Native Dialogs**: Uses zenity/kdialog on Linux for better file picker integration

## Requirements

- Python 3.6+
- FFmpeg (must be available in PATH)
- FFprobe (usually comes with FFmpeg)
- tkinter (usually included with Python)
- Optional: tkinterdnd2 (for drag-and-drop support)

## Installation

1. Install FFmpeg:
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg

   # Fedora
   sudo dnf install ffmpeg

   # macOS
   brew install ffmpeg
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/WyomingBb/FFmpeg-GUI-
   cd Ffmp-gui-app
   ```

3. (Optional) Install drag-and-drop support:
   ```bash
   pip install tkinterdnd2
   ```

## Usage

Run the application:
```bash
python app.py
```

### Basic Workflow

1. **Select Input**: Click "Browse" to choose a video file, or add multiple files to the batch list
2. **Choose Output**: Select an output folder and specify the output filename
3. **Select Format**: Choose from MP4, MKV, MOV, WebM, or GIF
4. **Apply Options** (optional):
   - Enable "Change FPS" to adjust frame rate
   - Enable "Trim clip" and use sliders to select start/end times
   - Use the preview slider to see thumbnails at different points
5. **Run**: Click "Run" to start processing

### Batch Processing

- Click "Add to batch" to select multiple files
- Drag and drop files into the batch list (if tkinterdnd2 is installed)
- Enable "Keep original names for batch" to preserve filenames
- Use the sort options to organize your batch list
- All files will be processed sequentially with the same settings

### Presets

Quick apply common configurations:
- **MP4 60fps**: High frame rate MP4
- **MP4 30fps**: Standard MP4
- **WebM 30fps**: Web-optimized WebM
- **GIF 10fps**: Animated GIF

## How It Works

The application uses FFmpeg under the hood with smart codec selection:

- **Copy mode**: When no filtering is needed, uses `-c copy` for fast re-muxing
- **Encoder detection**: Automatically detects available encoders (hardware acceleration support)
- **Decoder validation**: Checks if codecs can be decoded before processing
- **Optimized output**: Uses faststart flag for MP4/MOV for better streaming

## Limitations

- GIF output always uses scale filter (max 640px width)
- Hardware encoder availability depends on your FFmpeg build
- Trim and FPS changes require re-encoding (cannot use copy mode)

