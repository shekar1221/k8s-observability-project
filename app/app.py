import logging
import os
import random
import time
import uuid

from flask import Flask, Response, jsonify, request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Gauge, Histogram, generate_latest


SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "orders-api")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
APP_VERSION = os.getenv("APP_VERSION", "v1")

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
CART_ITEMS = Gauge("shopping_cart_items", "Current number of items in the demo cart")
CART_VALUE = Gauge("shopping_cart_value_usd", "Current total value of the demo cart in USD")
CHECKOUTS = Counter("shopping_cart_checkouts_total", "Total successful shopping cart checkouts")

PRODUCTS = {
    "p100": {"id": "p100", "name": "Laptop Backpack", "price": 49.99, "stock": 12},
    "p200": {"id": "p200", "name": "Wireless Mouse", "price": 24.99, "stock": 30},
    "p300": {"id": "p300", "name": "USB-C Hub", "price": 39.99, "stock": 18},
    "p400": {"id": "p400", "name": "Noise Cancelling Headphones", "price": 129.99, "stock": 8},
}
CART = {}
ORDERS = [
    {"id": "ord-1001", "status": "paid", "total": 49.99},
    {"id": "ord-1002", "status": "packed", "total": 24.99},
    {"id": "ord-1003", "status": "shipped", "total": 169.98},
]

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)


def simulate_latency(endpoint):
    latency_ms = random.randint(30, 180)
    time.sleep(latency_ms / 1000)
    REQUEST_LATENCY.labels(endpoint).observe(latency_ms / 1000)
    return latency_ms


def cart_summary():
    items = []
    total = 0.0
    count = 0
    for product_id, quantity in CART.items():
        product = PRODUCTS[product_id]
        line_total = round(product["price"] * quantity, 2)
        total += line_total
        count += quantity
        items.append(
            {
                "product_id": product_id,
                "name": product["name"],
                "price": product["price"],
                "quantity": quantity,
                "line_total": line_total,
            }
        )
    total = round(total, 2)
    CART_ITEMS.set(count)
    CART_VALUE.set(total)
    return {"items": items, "item_count": count, "total": total}


@app.after_request
def record_metrics(response):
    REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    return response


@app.get("/")
def home():
    logger.info("home endpoint called path=%s", request.path)
    return jsonify(
        service=SERVICE_NAME,
        version=APP_VERSION,
        message="Shopping cart observability demo",
        endpoints=[
            "GET /products",
            "GET /cart",
            "POST /cart/items",
            "DELETE /cart/items/<product_id>",
            "POST /checkout",
            "GET /orders",
            "GET /metrics",
            "GET /healthz",
        ],
    )


@app.get("/products")
def list_products():
    with tracer.start_as_current_span("catalog_lookup") as span:
        latency_ms = simulate_latency("/products")
        span.set_attribute("products.count", len(PRODUCTS))
        span.set_attribute("latency.ms", latency_ms)
        logger.info("products listed count=%s latency_ms=%s", len(PRODUCTS), latency_ms)
        return jsonify(products=list(PRODUCTS.values()))


@app.get("/cart")
def get_cart():
    with tracer.start_as_current_span("cart_read") as span:
        latency_ms = simulate_latency("/cart")
        summary = cart_summary()
        span.set_attribute("cart.item_count", summary["item_count"])
        span.set_attribute("cart.total", summary["total"])
        span.set_attribute("latency.ms", latency_ms)
        logger.info(
            "cart viewed item_count=%s total=%s latency_ms=%s",
            summary["item_count"],
            summary["total"],
            latency_ms,
        )
        return jsonify(cart=summary)


@app.post("/cart/items")
def add_cart_item():
    payload = request.get_json(silent=True) or {}
    product_id = payload.get("product_id")
    quantity = int(payload.get("quantity", 1))

    with tracer.start_as_current_span("cart_add_item") as span:
        latency_ms = simulate_latency("/cart/items")
        span.set_attribute("product.id", str(product_id))
        span.set_attribute("quantity", quantity)
        span.set_attribute("latency.ms", latency_ms)

        if product_id not in PRODUCTS:
            logger.warning("cart add failed reason=product_not_found product_id=%s", product_id)
            return jsonify(error="product_not_found", product_id=product_id), 404

        if quantity < 1:
            logger.warning("cart add failed reason=invalid_quantity quantity=%s", quantity)
            return jsonify(error="invalid_quantity", quantity=quantity), 400

        current_quantity = CART.get(product_id, 0)
        requested_quantity = current_quantity + quantity
        if requested_quantity > PRODUCTS[product_id]["stock"]:
            logger.warning(
                "cart add failed reason=insufficient_stock product_id=%s requested=%s stock=%s",
                product_id,
                requested_quantity,
                PRODUCTS[product_id]["stock"],
            )
            return jsonify(error="insufficient_stock", product_id=product_id), 409

        CART[product_id] = requested_quantity
        summary = cart_summary()
        logger.info(
            "cart item added product_id=%s quantity=%s cart_total=%s latency_ms=%s",
            product_id,
            quantity,
            summary["total"],
            latency_ms,
        )
        return jsonify(cart=summary), 201


@app.delete("/cart/items/<product_id>")
def remove_cart_item(product_id):
    with tracer.start_as_current_span("cart_remove_item") as span:
        latency_ms = simulate_latency("/cart/items/<product_id>")
        span.set_attribute("product.id", product_id)
        span.set_attribute("latency.ms", latency_ms)

        if product_id not in CART:
            logger.warning("cart remove failed reason=item_not_in_cart product_id=%s", product_id)
            return jsonify(error="item_not_in_cart", product_id=product_id), 404

        del CART[product_id]
        summary = cart_summary()
        logger.info(
            "cart item removed product_id=%s cart_total=%s latency_ms=%s",
            product_id,
            summary["total"],
            latency_ms,
        )
        return jsonify(cart=summary)


@app.post("/checkout")
def checkout():
    with tracer.start_as_current_span("checkout") as span:
        latency_ms = simulate_latency("/checkout")
        summary = cart_summary()
        span.set_attribute("cart.item_count", summary["item_count"])
        span.set_attribute("cart.total", summary["total"])
        span.set_attribute("latency.ms", latency_ms)

        if summary["item_count"] == 0:
            logger.warning("checkout failed reason=empty_cart latency_ms=%s", latency_ms)
            return jsonify(error="empty_cart"), 400

        order = {
            "id": f"ord-{uuid.uuid4().hex[:8]}",
            "status": "paid",
            "total": summary["total"],
            "items": summary["items"],
        }
        ORDERS.insert(0, order)
        CART.clear()
        cart_summary()
        CHECKOUTS.inc()
        logger.info(
            "checkout completed order_id=%s total=%s item_count=%s latency_ms=%s",
            order["id"],
            order["total"],
            len(order["items"]),
            latency_ms,
        )
        return jsonify(order=order), 201


@app.get("/orders")
def list_orders():
    with tracer.start_as_current_span("load_orders") as span:
        latency_ms = simulate_latency("/orders")
        span.set_attribute("orders.count", len(ORDERS))
        span.set_attribute("latency.ms", latency_ms)
        logger.info("orders loaded count=%s latency_ms=%s", len(ORDERS), latency_ms)
        return jsonify(orders=ORDERS[:10])


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
