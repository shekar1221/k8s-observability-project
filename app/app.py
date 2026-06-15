import logging
import os
import random
import time

from flask import Flask, Response, jsonify, request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram, generate_latest


SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "orders-api")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s service=%(name)s message=%(message)s",
)
logger = logging.getLogger(SERVICE_NAME)

resource = Resource.create({"service.name": SERVICE_NAME})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT)))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

REQUEST_COUNT = Counter(
    "orders_api_http_requests_total",
    "Total HTTP requests handled by orders-api",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "orders_api_request_latency_seconds",
    "Request latency for orders-api endpoints",
    ["endpoint"],
)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)


@app.after_request
def record_metrics(response):
    REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    return response


@app.get("/")
def home():
    logger.info("home endpoint called path=%s", request.path)
    return jsonify(
        service=SERVICE_NAME,
        message="Kubernetes observability demo",
        endpoints=["/", "/orders", "/metrics", "/healthz"],
    )


@app.get("/orders")
def list_orders():
    with REQUEST_LATENCY.labels("/orders").time():
        with tracer.start_as_current_span("load_orders") as span:
            simulated_latency_ms = random.randint(40, 240)
            time.sleep(simulated_latency_ms / 1000)
            span.set_attribute("orders.count", 3)
            span.set_attribute("latency.ms", simulated_latency_ms)
            logger.info("orders loaded count=3 latency_ms=%s", simulated_latency_ms)
            return jsonify(
                orders=[
                    {"id": "ord-1001", "status": "paid"},
                    {"id": "ord-1002", "status": "packed"},
                    {"id": "ord-1003", "status": "shipped"},
                ]
            )


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
