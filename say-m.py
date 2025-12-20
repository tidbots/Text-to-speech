#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import subprocess
import sys
from pathlib import Path
import termios
import tty
import re

PREFERRED_EN = ["Alex", "Samantha", "Daniel", "Karen", "Moira", "Arthur"]
AVOID = {
    "Albert", "Bad News", "Bells", "Boing", "Bubbles", "Cellos",
    "Good News", "Jester", "Organ", "Trinoids", "Whisper", "Zarvox"
}

EN_LOCALE_RE = re.compile(r"\ben_(US|GB|AU|CA|IE|IN|NZ|ZA|SG)\b", re.IGNORECASE)


def getkey() -> str:
    """通常キー/矢印キーを1回で取得"""
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
                if ch3 == "C":
                    return "RIGHT"
            return "ESC"
        return ch1
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def load_sentences(path: Path) -> list[str]:
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def say_voice_list_text() -> str:
    p = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("Failed to run: say -v ?")
    return p.stdout


def available_voices() -> set[str]:
    txt = say_voice_list_text()
    s = set()
    for line in txt.splitlines():
        parts = line.split()
        if parts:
            s.add(parts[0])
    return s


def pick_english_voice(requested: str | None) -> str:
    txt = say_voice_list_text()
    voices = available_voices()

    # 1) 指定があるなら「存在確認」して無ければ即エラー
    if requested:
        if requested not in voices:
            raise RuntimeError(f"Voice '{requested}' not found on this Mac.")
        return requested

    # 2) 定番優先（自然系）
    for v in PREFERRED_EN:
        if v in voices:
            return v

    # 3) en_* の行から拾う（ただし変わり種は除外）
    for line in txt.splitlines():
        if EN_LOCALE_RE.search(line) or "English" in line:
            name = line.split()[0]
            if name in AVOID:
                continue
            return name

    raise RuntimeError(
        "No English voice found. Install one in macOS settings:\n"
        "System Settings → Accessibility → Spoken Content → System Voice → Manage Voices\n"
        "and download an English voice (e.g., Alex/Samantha)."
    )


def speak(sentence: str, voice: str, rate: int | None):
    cmd = ["say", "-v", voice]
    if rate is not None:
        cmd += ["-r", str(rate)]
    # 失敗しても黙って進まないように check=True
    subprocess.run(cmd + [sentence], check=True)


def main():
    ap = argparse.ArgumentParser(description="macOS: arrow-key navigation + English TTS (no JP fallback).")
    ap.add_argument("file", help="Text file (1 sentence per line)")
    ap.add_argument("--voice", default=None, help="Voice name (optional). If omitted, auto-pick English.")
    ap.add_argument("--rate", type=int, default=None, help="Speech rate (WPM)")
    ap.add_argument("--print-voice", action="store_true", help="Print chosen voice and exit")
    args = ap.parse_args()

    sentences = load_sentences(Path(args.file))
    if not sentences:
        print("No sentences found.", file=sys.stderr)
        sys.exit(1)

    try:
        voice = pick_english_voice(args.voice)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        print("\nTry in Terminal:", file=sys.stderr)
        print("  say -v ? | grep -E \"en_US|en_GB|en_AU\"", file=sys.stderr)
        sys.exit(2)

    if args.print_voice:
        print(voice)
        return

    idx = 0
    print("=== 操作方法 ===")
    print("← : 前の文")
    print("→ : 次の文")
    print("Space : 読み上げ")
    print("q : 終了")
    print("================\n")
    print(f"Selected voice: {voice}\n")

    while True:
        print(f"\r[{idx+1}/{len(sentences)}] {sentences[idx]}      ", end="", flush=True)
        k = getkey()
        if k == "RIGHT" and idx < len(sentences) - 1:
            idx += 1
        elif k == "LEFT" and idx > 0:
            idx -= 1
        elif k == " ":
            try:
                speak(sentences[idx], voice, args.rate)
            except subprocess.CalledProcessError:
                print("\n[ERROR] 'say' failed. The selected voice may be unavailable.", file=sys.stderr)
                sys.exit(3)
        elif isinstance(k, str) and k.lower() == "q":
            print("\n終了します。")
            break


if __name__ == "__main__":
    main()

