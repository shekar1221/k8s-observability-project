import logging
import os
import random
import time

from flask import Response, request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram, generate_latest


def setup_observability(app, service_name):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s service=%(name)s message=%(message)s",
    )
    logger = logging.getLogger(service_name)

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    FlaskInstrumentor().instrument_app(app)

    request_count = Counter(
        f"{service_name.replace('-', '_')}_http_requests_total",
        f"Total HTTP requests handled by {service_name}",
        ["method", "endpoint", "status"],
    )
    request_latency = Histogram(
        f"{service_name.replace('-', '_')}_request_latency_seconds",
        f"Request latency for {service_name}",
        ["endpoint"],
    )

    @app.after_request
    def record_metrics(response):
        request_count.labels(request.method, request.path, response.status_code).inc()
        return response

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), mimetype="text/plain")

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "service": service_name}

    def simulate(endpoint):
        latency_ms = random.randint(20, 140)
        latency_ms += int(os.getenv("SIMULATED_EXTRA_LATENCY_MS", "0"))
        time.sleep(latency_ms / 1000)
        request_latency.labels(endpoint).observe(latency_ms / 1000)
        logger.info("request simulated endpoint=%s latency_ms=%s", endpoint, latency_ms)
        return latency_ms

    return logger, trace.get_tracer(service_name), simulate
