"""Sound playback with graceful degradation: winsound -> system player -> terminal bell."""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading

try:  # Windows only
    import winsound
except ImportError:  # pragma: no cover - non-Windows
    winsound = None  # type: ignore[assignment]


class SoundPlayer:
    """play(sound) starts repeating sound until stop(). `sound` is 'beep', 'silent' or a .wav path."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._proc: subprocess.Popen | None = None
        self.backend = "none"

    # ---- public ----
    def play(self, sound: str) -> None:
        self.stop()
        if sound == "silent":
            self.backend = "silent"
            return
        self._stop.clear()
        if sound != "beep":
            if self._play_wav(sound):
                return
        self.backend = "winsound" if winsound else "terminal bell"
        self._thread = threading.Thread(target=self._beep_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if winsound:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except RuntimeError:
                pass
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None
        if self._thread:
            self._thread.join(timeout=1.5)
            self._thread = None

    # ---- backends ----
    def _beep_loop(self) -> None:
        while not self._stop.is_set():
            if winsound:
                for freq in (880, 1175, 880, 1175):
                    if self._stop.is_set():
                        return
                    winsound.Beep(freq, 150)
            else:
                sys.stdout.write("\a")
                sys.stdout.flush()
            self._stop.wait(0.6)

    def _play_wav(self, path: str) -> bool:
        if winsound:
            try:
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
                self.backend = "winsound (wav)"
                return True
            except RuntimeError:
                return False
        for exe, args in (("afplay", []), ("paplay", []), ("aplay", ["-q"])):
            if shutil.which(exe):
                self.backend = f"{exe} (wav)"
                self._thread = threading.Thread(target=self._wav_loop, args=(exe, args, path), daemon=True)
                self._thread.start()
                return True
        return False

    def _wav_loop(self, exe: str, args: list[str], path: str) -> None:
        while not self._stop.is_set():
            self._proc = subprocess.Popen([exe, *args, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            while self._proc.poll() is None and not self._stop.is_set():
                self._stop.wait(0.1)


class FakePlayer:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.playing = False
        self.backend = "fake"

    def play(self, sound: str) -> None:
        self.calls.append(f"play:{sound}")
        self.playing = True

    def stop(self) -> None:
        if self.playing:
            self.calls.append("stop")
        self.playing = False
