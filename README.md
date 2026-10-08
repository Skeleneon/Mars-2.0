# Mars

A Python-based voice assistant for Windows. Mars listens for spoken commands, recognizes them offline, and responds out loud, with a simple desktop GUI.

## Features

- **Offline speech recognition** using [Vosk](https://alphacephei.com/vosk/)
- **Spoken responses** via gTTS and pygame
- **Desktop GUI** built with Tkinter
- **System volume control** through pycaw
- **Background threading** (daemon threads) so the UI stays responsive while listening
- **Standalone build** with PyInstaller

## Tech Stack

| Area | Tool |
|---|---|
| Language | Python |
| GUI | Tkinter |
| Speech recognition | Vosk (`vosk-model-small-en-us-0.15`) |
| Text-to-speech | gTTS + pygame |
| Audio control | pycaw / comtypes |
| Packaging | PyInstaller |

## Getting Started

### Prerequisites

- Windows 10/11
- Python 3.x
- A working microphone



Download the Vosk model and extract it into the project folder in /subfiles/Speech Models:

- [vosk-model-small-en-us-0.15](https://alphacephei.com/vosk/models)

### Run

Run from the project root so relative asset paths to resolve correctly
You can also build using Pyinstaller by running to create a native executable

```bash
pyinstaller --clean main.spec
```


## Project Structure

```
mars/
├── assets/          # Icons and other static files
├── subfiles/        # extra files necessary to run Mars
├── logs/            # Runtime logs made by Mars(Work in Progress)
├── main.py          # Entry point
└── requirements.txt
```

## Notes

- Asset paths are relative, so launching from a different working directory can break them. When using Windows Task Scheduler, set the **Start in** field to the project folder.
- Task Scheduler must run Mars in an interactive session; Session 0 can't show the GUI or access audio devices.

