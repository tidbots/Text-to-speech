#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import hashlib
import subprocess
import sys
import threading
from pathlib import Path
import termios
import tty

from TTS.api import TTS
import torch


def getkey() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch1 = sys.stdin.read(1)
        if ch1 == "\x1b":  # ESC
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                if ch3 == "D":
                    return "LEFT"
                elif ch3 == "C":
                    return "RIGHT"
        return ch1
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def load_sentences(path: Path) -> list[str]:
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def play_wav(path: str):
    subprocess.run(["aplay", "-q", path], check=False)


def sha_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


class WavCache:
    def __init__(self, tts: TTS, cache_dir: Path):
        self.tts = tts
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._inflight: set[str] = set()

    def wav_path(self, text: str) -> Path:
        return self.cache_dir / f"{sha_id(text)}.wav"

    def is_cached(self, text: str) -> bool:
        p = self.wav_path(text)
        return p.exists() and p.stat().st_size > 0

    def ensure(self, text: str) -> Path:
        out = self.wav_path(text)
        if out.exists() and out.stat().st_size > 0:
            return out

        key = out.name
        with self._lock:
            if key in self._inflight:
