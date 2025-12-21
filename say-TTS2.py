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

import torch
from TTS.api import TTS


MODEL_XTTS_V2 = "tts_models/multilingual/multi-dataset/xtts_v2"


def getkey() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch1 = sys.stdin.read(1)
        if ch1 == "\x1b":
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


def sid(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


class WavCacheXTTS:
    def __init__(self, tts: TTS, cache_dir: Path, lang: str, speaker_idx: str, speaker_wav: str | None):
        self.tts = tts
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.lang = lang
        self.speaker_idx = speaker_idx
        self.speaker_wav = speaker_wav
        self._lock = threading.Lock()
        self._inflight: set[str] = set()

    def wav_path(self, text: str) -> Path:
        # lang / speaker 条件が変わると音声が変わるのでIDに含める
        tag = f"{self.lang}|{self.speaker_wav or self.speaker_idx}"
        h = hashlib.sha1((tag + "|" + text).encode("utf-8")).hexdigest()[:12]
        return self.cache_dir / f"{h}.wav"

    def is_cached(self, text: str) -> bool:
        p = self.wav_path(text)
        return p.exists() and p.stat().st_size > 0

    def _kwargs(self) -> dict:
        kw = {"language": self.lang}
        if self.speaker_wav:
            kw["speaker_wav"] = self.speaker_wav
        else:
            kw["speaker"] = self.speaker_idx
        return kw

    def ensure(self, text: str) -> Path:
        out = self.wav_path(text)
        if out.exists() and out.stat().st_size > 0:
            return out

        key = out.name
        with self._lock:
            if key in self._inflight:
                pass
            else:
                self._inflight.add(key)

        try:
            tmp = out.with_suffix(".tmp.wav")
            self.tts.tts_to_file(text=text, file_path=str(tmp), **self._kwargs())
            tmp.replace(out)
            return out
        finally:
            with self._lock:
                self._inflight.discard(key)

    def prefetch(self, text: str):
        out = self.wav_path(text)
        if out.exists() and out.stat().st_size > 0:
            return

        key = out.name
        with self._lock:
            if key in self._inflight:
                return
            self._inflight.add(key)

        def _job():
            try:
                tmp = out.with_suffix(".tmp.wav")
                self.tts.tts_to_file(text=text, file_path=str(tmp), **self._kwargs())
                tmp.replace(out)
            except Exception:
                pass
            finally:
                with self._lock:
                    self._inflight.discard(key)

        threading.Thread(target=_job, daemon=True).start()


def warmup_all(sentences: list[str], cache: WavCacheXTTS):
    total = len(sentences)
    skipped = 0
    print("\nWarmup(all): generating wav cache...")
    for i, s in enumerate(sentences, start=1):
        if cache.is_cached(s):
            skipped += 1
        else:
            cache.ensure(s)
        if i % 5 == 0 or i == total:
            print(f"\rWarmup: {i}/{total} (skipped {skipped})", end="", flush=True)
    print("\nWarmup done.\n")


def main():
    ap = argparse.ArgumentParser(description="GPU + XTTS v2 + warmup(all) + arrow keys")
    ap.add_argument("file", help="1行1文テキスト")
    ap.add_argument("--lang", default="en", help="language (default: en)")
    ap.add_argument("--speaker_idx", default="Ana Florence", help="built-in speaker name")
    ap.add_argument("--speaker_wav", default=None, help="reference wav (voice clone)")
    ap.add_argument("--cache_dir", default=".tts_cache_xtts", help="wav cache directory")
    ap.add_argument("--warmup", choices=["none", "all"], default="none", help="all: 起動時に全行生成")
    ap.add_argument("--no_prefetch", action="store_true", help="先読みを無効化")
    ap.add_argument("--cpu", action="store_true", help="強制CPU（GPUがあっても使わない）")
    args = ap.parse_args()

    sentences = load_sentences(Path(args.file))
    if not sentences:
        print("No sentences found.", file=sys.stderr)
        sys.exit(1)

    use_gpu = (not args.cpu) and torch.cuda.is_available()
    print(f"Loading XTTS v2... ({'GPU' if use_gpu else 'CPU'})")
    if use_gpu:
        print("GPU:", torch.cuda.get_device_name(0))

    tts = TTS(model_name=MODEL_XTTS_V2, progress_bar=False, gpu=use_gpu)
    cache = WavCacheXTTS(
        tts=tts,
        cache_dir=Path(args.cache_dir),
        lang=args.lang,
        speaker_idx=args.speaker_idx,
        speaker_wav=args.speaker_wav,
    )

    if args.warmup == "all":
        warmup_all(sentences, cache)

    idx = 0
    print("←/→: move   Space: speak   q: quit")
    print(f"lang={args.lang}  cache_dir={args.cache_dir}  warmup={args.warmup}")
    print("voice:", f"speaker_wav={args.speaker_wav}" if args.speaker_wav else f"speaker_idx={args.speaker_idx}")
    print()

    if not args.no_prefetch and len(sentences) > 1:
        cache.prefetch(sentences[1])

    while True:
        print(f"\r[{idx+1}/{len(sentences)}] {sentences[idx]}      ", end="", flush=True)
        k = getkey()

        if k == "RIGHT" and idx < len(sentences) - 1:
            idx += 1
            if not args.no_prefetch and idx + 1 < len(sentences):
                cache.prefetch(sentences[idx + 1])

        elif k == "LEFT" and idx > 0:
            idx -= 1
            if not args.no_prefetch and idx + 1 < len(sentences):
                cache.prefetch(sentences[idx + 1])

        elif k == " ":
            wav = cache.ensure(sentences[idx])
            play_wav(str(wav))
            if not args.no_prefetch and idx + 1 < len(sentences):
                cache.prefetch(sentences[idx + 1])

        elif isinstance(k, str) and k.lower() == "q":
            print("\nBye.")
            break


if __name__ == "__main__":
    main()
