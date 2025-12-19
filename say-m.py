#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import subprocess
import sys
from pathlib import Path
import termios
import tty


def getch() -> str:
    """1文字だけキー入力を取得（Enter不要）"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def speak_lines(path: Path, voice: str | None, rate_wpm: int | None):
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    cmd_base = ["say"]
    if voice:
        cmd_base += ["-v", voice]
    if rate_wpm is not None:
        cmd_base += ["-r", str(rate_wpm)]

    print("=== 操作方法 ===")
    print("Space : 次の文を読む")
    print("q     : 終了")
    print("================\n")

    with path.open("r", encoding="utf-8") as f:
        for i, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue

            print(f"[{i}] {line}")
            print("→ Space を押してください", end="", flush=True)

            while True:
                key = getch()
                if key == " ":
                    print("\r", end="")
                    subprocess.run(cmd_base + [line])
                    break
                elif key.lower() == "q":
                    print("\n終了します。")
                    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Read an English text file aloud. Press SPACE to go to the next sentence."
    )
    parser.add_argument("file", help="Path to text file (1 sentence per line)")
    parser.add_argument("--voice", help="Voice name (e.g., Samantha, Alex)")
    parser.add_argument("--rate", type=int, help="Speech rate (WPM)")
    args = parser.parse_args()

    speak_lines(Path(args.file), args.voice, args.rate)


if __name__ == "__main__":
    main()

