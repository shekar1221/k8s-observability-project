import re
import statistics
import sys


LATENCY_PATTERN = re.compile(r"latency_ms=(\d+)")


def extract_latencies(lines):
    latencies = []
    for line in lines:
        match = LATENCY_PATTERN.search(line)
        if match:
            latencies.append(int(match.group(1)))
    return latencies


def percentile(values, percentile_value):
    if not values:
        return None
    sorted_values = sorted(values)
    index = round((percentile_value / 100) * (len(sorted_values) - 1))
    return sorted_values[index]


def summarize(latencies):
    if not latencies:
        return {"count": 0, "message": "No latency_ms values found"}

    return {
        "count": len(latencies),
        "min_ms": min(latencies),
        "avg_ms": round(statistics.mean(latencies), 2),
        "p95_ms": percentile(latencies, 95),
        "max_ms": max(latencies),
    }


def main():
    latencies = extract_latencies(sys.stdin)
    print(summarize(latencies))


if __name__ == "__main__":
    main()
