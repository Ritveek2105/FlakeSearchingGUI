# Graphene Pipeline

Python tools for correcting microscope tiles, stitching them with Fiji/MIST,
detecting graphene flakes, generating Deep Zoom assets, and publishing samples
to the companion `stitched-ui` viewer.

## Requirements

- Python 3.11 or newer
- Fiji/ImageJ with MIST available as an executable
- Optional: Roboflow API key for automatic flake detection
- Optional: the companion `stitched-ui` folder if you want to publish samples to the web viewer

## Install From A Download

For a simple local launch on Windows, double-click:

```text
start-pipeline-gui.bat
```

The launcher creates `.venv/` if needed, installs the package in editable mode, loads `.env` if present, and starts the desktop GUI.

Manual install:

From the folder containing this project:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

For a wheel release:

```powershell
python -m pip install graphene_pipeline-0.1.0-py3-none-any.whl
```

## Configure

Copy `.env.example` to `.env` and set values as needed. The most important settings are:

```powershell
$env:GRAPHENE_PIPELINE_HOME = "C:\path\to\your\workspace"
$env:FIJI_EXE = "C:\path\to\Fiji\fiji-windows-x64.exe"
$env:GRAPHENE_WEBSITE_DIR = "C:\path\to\stitched-ui"
$env:ROBOFLOW_API_KEY = "your_key_here"
```

If `GRAPHENE_PIPELINE_HOME` is not set, the pipeline writes `data/`, `runs/`, `logs/`, and `reports/` into the directory where you run the command.

## Run

Show CLI help:

```powershell
graphene-pipeline --help
```

Run a full pipeline:

```powershell
graphene-pipeline --raw-folder "C:\path\to\raw_tiles"
```

Launch the desktop GUI:

```powershell
graphene-pipeline-gui
```

Launch the acquisition helper:

```powershell
graphene-acquisition-gui
```

## Development Checks

```powershell
python -m pytest
python -m pip wheel --no-deps . -w dist
```

## Release Notes

Do not ship generated runtime folders in source downloads:

- `.venv/`
- `data/`
- `logs/`
- `reports/`
- `runs/`
- `build/`
- `dist/`
- `*.egg-info/`
