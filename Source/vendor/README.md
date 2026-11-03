# vendor/

Helper programs that get bundled inside `RetroGrab.exe`. They're not in git (too big).

`build.py` fills this folder automatically from your PC (after `setup.bat`):

| File | Why |
|---|---|
| `ffmpeg.exe`, `ffprobe.exe` (+ DLLs) | merging video + audio, converting to MP3, embedding covers |
| `deno.exe` **or** `node.exe` **or** `qjs.exe` | YouTube needs a JavaScript runtime |
| `versions.json` | generated - records which engine versions were bundled |

To bundle different builds (e.g. smaller ones), put them here before running `build.py`;
files already present are kept.
