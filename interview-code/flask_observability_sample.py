import random
import time

from flask import Flask, Response
from prometheus_client import Counter, Histogram, generate_latest


app = Flask(__name__)

REQUEST_COUNT = Counter(
    "demo_http_requests_total",
    "Total HTTP requests handled by the demo app",
    ["endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "demo_request_latency_seconds",
    "Request latency for the demo app",
    ["endpoint"],
)


@app.get("/healthz")
def healthz():
    REQUEST_COUNT.labels("/healthz", "200").inc()
    return {"status": "ok"}


@app.get("/work")
def work():
    started = time.perf_counter()
    latency_ms = random.randint(50, 500)
    time.sleep(latency_ms / 1000)
    elapsed = time.perf_counter() - started

    REQUEST_COUNT.labels("/work", "200").inc()
    REQUEST_LATENCY.labels("/work").observe(elapsed)
    return {"message": "work completed", "latency_ms": latency_ms}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
