"""RetroGrab entry point."""
import io
import os
import sys


class _NullStream(io.TextIOBase):
    """Windowed .exe builds have no console; libraries that print must not crash."""

    def write(self, s):
        return len(s)

    def isatty(self):
        return False


for _name in ("stdout", "stderr"):
    if getattr(sys, _name) is None:
        setattr(sys, _name, _NullStream())


def main():
    if "--ig-login" in sys.argv:
        import login
        sys.exit(login.run())

    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    # No custom AppUserModelID on purpose: the default one (derived from RetroGrab.exe)
    # matches taskbar pins and shortcuts, so a pinned RetroGrab groups with its window
    # and keeps the exe's icon.
    if not getattr(sys, "frozen", False):  # from source, python.exe would steal the taskbar group/icon
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RetroGrab.Source")
        except Exception:
            pass

    import updater
    versions = updater.activate()  # must run before yt_dlp / gallery_dl are imported

    if "--test-update" in sys.argv:  # hidden: install the latest release over this copy (for testing)
        import appupdate
        info = appupdate.check(current="0")
        appupdate.install_and_restart(appupdate.download(info))
        sys.exit(0)

    if "--selftest" in sys.argv:  # writes a diagnostics report, used when building/troubleshooting
        import json
        import common
        import gallery_dl
        import yt_dlp
        from gallery_dl import extractor
        report = {"versions": versions, "yt_dlp_file": yt_dlp.__file__, "gallery_dl_file": gallery_dl.__file__,
                  "ffmpeg": common.ffmpeg_location(), "js": common.js_runtimes(), "frozen": common.FROZEN,
                  "gallery_dl_instagram": type(extractor.find("https://www.instagram.com/p/C0000000000/")).__name__}
        if "full" in sys.argv:  # tiny real download through the whole engine
            import threading
            import engine

            class Rep:
                def __init__(self):
                    self.lines, self.files = [], []

                def log(self, m): self.lines.append(m)
                def status(self, m): pass
                def title(self, m): pass
                def progress(self, *a): pass
                def saved(self, p, s): self.files.append(p)

            try:
                report["qualities"] = engine.video_qualities("https://www.youtube.com/watch?v=jNQXAC9IVRw")
            except Exception as e:
                report["qualities"] = f"FAILED: {e}"
            for svc, url, o in (
                ("YouTube", "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                 {"mode": "Video + Audio", "quality": "144p", "height_limit": 144, "fmt": "mp4", "thumb": True}),
                ("Spotify", "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
                 {"fmt": "mp3", "quality": "128 kbps", "subfolder": False, "skip_existing": False}),
            ):
                o["folder"] = os.path.join(common.DATA, "selftest_downloads")
                rep = Rep()
                try:
                    engine.RUNNERS[svc]({"url": url, "opts": o}, rep, threading.Event())
                    report[svc] = {"ok": True, "files": rep.files}
                except Exception as e:
                    report[svc] = {"ok": False, "error": str(e), "log": rep.lines[-15:]}
        with open(os.path.join(common.DATA, "selftest.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        sys.exit(0)

    import tkinter as tk
    from app import App
    from common import ASSETS

    root = tk.Tk()
    ico = os.path.join(ASSETS, "retrograb.ico")
    if os.path.isfile(ico):
        try:
            root.iconbitmap(default=ico)
        except tk.TclError:
            pass
    App(root, versions)
    root.mainloop()


if __name__ == "__main__":
    main()
