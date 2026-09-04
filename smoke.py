import sys
import time

from backend.config import Config
from backend.downloader import DownloadManager

URL = sys.argv[1] if len(sys.argv) > 1 else (
    "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/"
    "Big_Buck_Bunny_360_10s_1MB.mp4")


def main():
    m = DownloadManager(Config(), lambda e: None, max_workers=1)
    tid = m.add_task(URL)
    deadline = time.time() + 180
    while time.time() < deadline:
        t = m.tasks[tid]
        print(f"\r{t.status.value:12s} {t.percent:5.1f}% {t.speed}", end="", flush=True)
        if t.status.value in ("done", "error", "cancelled"):
            print()
            print(t.to_dict())
            sys.exit(0 if t.status.value == "done" else 1)
        time.sleep(0.5)
    print("\n超时")
    sys.exit(1)


if __name__ == "__main__":
    main()
