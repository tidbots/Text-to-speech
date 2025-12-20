#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import subprocess
import sys
from pathlib import Path
import termios
import tty


def getkey() -> str:
    """
    1キー取得
    通常キー: ' ', 'q'
    矢印キー: 'LEFT', 'RIGHT'
    """
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


def speak(sentence: str, voice: str, rate: int):
    # stdout/stderr を捨ててターミナル表示を乱さない
    subprocess.run(
        ["espeak-ng", "-v", voice, "-s", str(rate), sentence],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Ubuntu TTS reader with arrow-key navigation (English only)."
    )
    parser.add_argument("file", help="Text file (1 sentence per line)")
    parser.add_argument(
        "--voice",
        default="en-us",
        help="espeak-ng English voice (default: en-us)"
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=175,
        help="Speech rate (default: 175)"
    )
    args = parser.parse_args()

    sentences = load_sentences(Path(args.file))
    if not sentences:
        print("No sentences found.", file=sys.stderr)
        sys.exit(1)

    idx = 0

    print("=== 操作方法 ===")
    print("← : 前の文")
    print("→ : 次の文")
    print("Space : 読み上げ")
    print("q : 終了")
    print("================\n")
    print(f"Voice: {args.voice}  Rate: {args.rate}\n")

    while True:
        print(
            f"\r[{idx+1}/{len(sentences)}] {sentences[idx]}      ",
            end="",
            flush=True,
        )

        key = getkey()

        if key == "RIGHT" and idx < len(sentences) - 1:
            idx += 1
        elif key == "LEFT" and idx > 0:
            idx -= 1
        elif key == " ":
            speak(sentences[idx], args.voice, args.rate)
        elif isinstance(key, str) and key.lower() == "q":
            print("\n終了します。")
            break


if __name__ == "__main__":
    main()
