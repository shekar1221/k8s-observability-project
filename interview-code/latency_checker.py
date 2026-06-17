import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


def check_url(url, timeout_seconds=5):
    started = time.perf_counter()
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            response.read()
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "url": url,
                "status": response.status,
                "latency_ms": round(elapsed_ms, 2),
                "ok": 200 <= response.status < 400,
            }
    except URLError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "url": url,
            "status": "ERROR",
            "latency_ms": round(elapsed_ms, 2),
            "ok": False,
            "error": str(exc),
        }


def main():
    urls = sys.argv[1:]
    if not urls:
        urls = ["http://localhost:8080/healthz"]

    for url in urls:
        result = check_url(url)
        print(result)


if __name__ == "__main__":
    main()
