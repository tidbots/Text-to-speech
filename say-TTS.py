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
    # Ubuntu標準なら aplay。無い場合は: sudo apt install alsa-utils
    subprocess.run(["aplay", "-q", path], check=False)


def sha_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


class WavCache:
    """
    文(text) -> wavファイル をキャッシュする
    - 生成中は同じ文を二重生成しない
    - 先読み(prefetch)で次文をバックグラウンド生成
    """
    def __init__(self, tts: TTS, cache_dir: Path):
        self.tts = tts
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._inflight: set[str] = set()

    def wav_path(self, text: str) -> Path:
        # 同一文は同一ファイル名（SHA1先頭12桁）
        return self.cache_dir / f"{sha_id(text)}.wav"

    def ensure(self, text: str) -> Path:
        out = self.wav_path(text)
        if out.exists() and out.stat().st_size > 0:
            return out

        key = out.name
        with self._lock:
            if key in self._inflight:
                # 他スレッド生成中なら待つ（簡易ポーリング）
                pass
            else:
                self._inflight.add(key)

        try:
            # tmpに書いてから置換（途中失敗で壊れたwavを残さない）
            tmp = out.with_suffix(".tmp.wav")
            self.tts.tts_to_file(text=text, file_path=str(tmp))
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
                self.tts.tts_to_file(text=text, file_path=str(tmp))
                tmp.replace(out)
            except Exception:
                pass
            finally:
                with self._lock:
                    self._inflight.discard(key)

        threading.Thread(target=_job, daemon=True).start()


def main():
    ap = argparse.ArgumentParser(description="Ubuntu high-quality TTS with WAV cache (arrow keys).")
    ap.add_argument("file", help="1行1文のテキスト")
    ap.add_argument("--model", default="tts_models/en/ljspeech/vits", help="Coqui TTS model")
    ap.add_argument("--cpu", action="store_true", help="強制CPU")
    ap.add_argument("--cache_dir", default=".tts_cache", help="wavキャッシュ保存先")
    ap.add_argument("--no_prefetch", action="store_true", help="先読みを無効化")
    args = ap.parse_args()

    sentences = load_sentences(Path(args.file))
    if not sentences:
        print("No sentences found.", file=sys.stderr)
        sys.exit(1)

    use_gpu = (not args.cpu) and torch.cuda.is_available()
    print(f"Loading TTS model... ({'GPU' if use_gpu else 'CPU'})")
    tts = TTS(model_name=args.model, progress_bar=False, gpu=use_gpu)

    cache = WavCache(tts, Path(args.cache_dir))

    idx = 0
    print("\n←/→: move   Space: speak   q: quit")
    print(f"model={args.model}")
    print(f"cache_dir={args.cache_dir}\n")

    # 最初に次文を先読み
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
