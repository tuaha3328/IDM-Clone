# IDM Clone

## Run from source

Install Python 3.10 or later, then double-click `run.bat` (or run it from a
terminal). It creates a project virtual environment, installs the requirements,
and launches the app. Alternatively, from the project directory run:

```powershell
python -m pip install -r requirements.txt
python main.py
```

The first run requires an internet connection to install dependencies. The
requirements include yt-dlp and `imageio-ffmpeg`; the latter supplies the
FFmpeg executable used for YouTube video merging and MP3 extraction. No separate
FFmpeg installation or PATH configuration is needed.

## Build a standalone Windows app

On Windows, install Python 3.10 or later and run these commands from the project
directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\build.ps1
```

The distributable is `dist\IDM-Clone.exe`. It bundles the Python runtime,
application dependencies, yt-dlp, and the FFmpeg executable. Users can run the
EXE without installing Python or the project dependencies. Build separately on
each target operating system; this script produces a Windows executable.
