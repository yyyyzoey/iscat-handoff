import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("start", nargs="?", type=int, default=1)
    parser.add_argument("end", nargs="?", type=int, default=0)
    args = parser.parse_args()
    lines = Path(args.path).read_text(encoding="utf-8").splitlines()
    end = args.end or len(lines)
    for number in range(max(1, args.start), min(len(lines), end) + 1):
        print(f"{number:6d}: {lines[number - 1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
