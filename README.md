<p align="center">
  <img src="Source/assets/logo.png" alt="RetroGrab logo" width="180">
</p>

<h1 align="center">RetroGrab</h1>

<p align="center">
A Windows 95-style desktop downloader for <b>YouTube</b>, <b>Instagram</b> and <b>Spotify</b> links.<br>
Paste a link, pick your options, hit <b>Download</b>.
</p>

- **YouTube** — videos, Shorts, playlists. Video + audio, video only, or audio only. Resolution from 144p to 4K, MP4 / MKV / WebM, MP3 / M4A / Opus / WAV / FLAC, subtitles and thumbnails.
- **Instagram** — reels, posts and carousels (all photos + videos), or just the audio as MP3.
- **Spotify** — songs, albums and playlists. Each song is matched on YouTube by title, artist and length, then saved as MP3 / M4A tagged with the Spotify title, artist, album and cover art. If a song exists in several languages (common for Indian film songs: Tamil / Telugu / Hindi / Kannada / Malayalam …), RetroGrab **asks which language you want**, and can remember the choice for a whole album or playlist. *Spotify's own DRM-protected audio is never downloaded.*
- Download queue, progress bar, history, and a built-in updater for the download engines.

## Download & run (no install needed)

> [!IMPORTANT]
> **Don't use the green "Code → Download ZIP" button.** That's the source code and needs Python.
> Download the ready-to-run app from **[Releases](../../releases/latest)** instead.

1. Go to [**Releases**](../../releases/latest) and download `RetroGrab-x.x.x-win64.zip` (under *Assets*).
2. Unzip the whole folder somewhere you can write to (Documents, Desktop, `D:\` …). Don't run it from inside the zip.
3. Double-click **`RetroGrab.exe`**. For a Desktop shortcut: right-click it, then **Send to > Desktop (create shortcut)**.
4. If Windows shows *"Windows protected your PC"*, click **More info**, then **Run anyway**. This appears for any app that isn't code-signed.

**Nothing else to install.** Python, yt-dlp, gallery-dl, ffmpeg and a JavaScript runtime are all inside the zip, and the app never uses copies installed on the PC.

| Requirement | Notes |
|---|---|
| Windows 10 or 11, 64-bit | Windows on ARM works too, through Windows' built-in x64 emulation. Windows 7/8 are not supported. |
| Internet connection | for downloading, obviously |
| Microsoft Edge WebView2 | **only** for the Instagram login window. Already included in Windows 11 and up-to-date Windows 10. If the login window won't open, install the free [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/). |

### Instagram login: what happens to your account
Most Instagram links need a login. On the Instagram tab, click **Log in to Instagram…**. The app explains the steps below first (and again any time under **Privacy…**):

1. **You log in on Instagram's own page**, `instagram.com`, inside a private (InPrivate) Microsoft Edge window. Your username and password go only to Instagram. RetroGrab never reads, sees or stores them.
2. **Only Instagram's session cookie is kept.** This is the same "stay logged in" token your browser keeps. RetroGrab encrypts it with **Windows DPAPI** before writing it to `data\instagram_session.bin`. Only your Windows account on that PC can decrypt it, so a copied file is useless anywhere else.
3. **The browser window leaves nothing behind.** Its temporary folder is deleted as soon as it closes.
4. **The session is only ever sent to instagram.com**, to download what you ask for. RetroGrab has no servers, accounts, analytics or telemetry.
5. **Log out** deletes the session file. For extra safety, Instagram's **Settings > Accounts Center > Password and security > Where you're logged in** can end the session from Instagram's side too.

Don't take our word for it: the login code is short and readable, in [`Source/login.py`](Source/login.py) and the *Instagram session* part of [`Source/common.py`](Source/common.py).

### When something stops working
YouTube and Instagram change often. Use **Tools > Check for updates**, then restart. This downloads the latest yt-dlp / gallery-dl from PyPI (checksum-verified) without needing a new exe. **Tools > Show log** shows what went wrong.

## Your data stays on your PC

RetroGrab has no accounts, servers, analytics or telemetry. It only talks to the sites you paste links from, plus PyPI when you check for updates. Everything it stores lives next to the program:

| Folder | Contents |
|---|---|
| `data\` | settings, download history, a local log (`retrograb.log`), the encrypted Instagram session, engine updates |
| `Downloads\` | your files, in `YouTube\`, `Instagram\`, `Spotify\` (changeable in the app) |

If the folder isn't writable (e.g. inside Program Files), it falls back to `%APPDATA%\RetroGrab`.
None of these are ever included in this repo or in the release zip.

## Run or build from source

Needs [Python 3.10+](https://www.python.org/downloads/) (tick *Add python.exe to PATH*).

```bat
git clone <this repo>
cd RetroGrab
setup.bat      :: installs Python packages + ffmpeg + Deno (via winget) if missing
:: open a NEW terminal window so ffmpeg/deno are on PATH, then:
run.bat        :: start from source
build.bat      :: make App\RetroGrab.exe and Release\RetroGrab-x.x.x-win64.zip
```

When running from source, data goes in `Source\.devdata\` (git-ignored).

## Project layout

```
App/          built program (RetroGrab.exe + _internal, and data/)  - created by build.bat
Downloads/    your downloads                                        - git-ignored
Release/      shareable zip                                         - created by build.bat
Source/
  retrograb.py   entry point (+ --ig-login, --selftest [full])
  app.py         main window: tabs, queue, history
  retro.py       Win95 widgets (title bar, tabs, block progress bar)
  engine.py      YouTube / Instagram / Spotify download logic
  spotify.py     Spotify metadata, YouTube matching, tagging
  login.py       Instagram login window (WebView2)
  updater.py     engine self-updater (PyPI wheels)
  common.py      paths and helpers
  build.py       PyInstaller build
  make_icon.py   turns assets/logo_source.png into logo.png, retrograb.ico, titlebar.png
  vendor/        ffmpeg + JS runtime bundled into the exe (filled by build.py)
Archive/      the first, simpler yt-dlp front-end
```

## Please download responsibly

Only download content you own or have permission to save. Downloading from YouTube or Instagram, or saving music, may break those sites' terms of service and copyright law where you live. You are responsible for how you use this tool.

## Built on

[yt-dlp](https://github.com/yt-dlp/yt-dlp) · [gallery-dl](https://github.com/mikf/gallery-dl) · [FFmpeg](https://ffmpeg.org) · [pywebview](https://pywebview.flowrl.com) · [mutagen](https://github.com/quodlibet/mutagen) · [PyInstaller](https://pyinstaller.org)
