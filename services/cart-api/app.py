import json
import os

import redis
from flask import Flask, jsonify, request

from common.observability import setup_observability


SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "cart-api")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
PRODUCTS = {
    "p100": {"id": "p100", "name": "Laptop Backpack", "price": 49.99},
    "p200": {"id": "p200", "name": "Wireless Mouse", "price": 24.99},
    "p300": {"id": "p300", "name": "USB-C Hub", "price": 39.99},
    "p400": {"id": "p400", "name": "Noise Cancelling Headphones", "price": 129.99},
}
FALLBACK_CART = {}

app = Flask(__name__)
logger, tracer, simulate = setup_observability(app, SERVICE_NAME)


def redis_client():
    return redis.Redis(host=REDIS_HOST, port=6379, socket_connect_timeout=1, decode_responses=True)


def read_cart(user_id):
    try:
        raw = redis_client().get(f"cart:{user_id}")
        return json.loads(raw) if raw else {}
    except Exception as exc:
        logger.warning("redis unavailable fallback=in_memory error=%s", exc)
        return FALLBACK_CART.get(user_id, {})


def write_cart(user_id, cart):
    try:
        redis_client().set(f"cart:{user_id}", json.dumps(cart))
    except Exception:
        FALLBACK_CART[user_id] = cart


def summarize(cart):
    items = []
    total = 0
    for product_id, quantity in cart.items():
        product = PRODUCTS[product_id]
        line_total = round(product["price"] * quantity, 2)
        total += line_total
        items.append({**product, "quantity": quantity, "line_total": line_total})
    return {"items": items, "total": round(total, 2), "item_count": sum(cart.values())}


@app.get("/")
def home():
    return {"service": SERVICE_NAME, "endpoints": ["/cart/<user_id>", "/cart/items", "/cart/clear", "/metrics", "/healthz"]}


@app.get("/cart/<user_id>")
def get_cart(user_id):
    with tracer.start_as_current_span("cart_read"):
        simulate("/cart/<user_id>")
        summary = summarize(read_cart(user_id))
        logger.info("cart read user_id=%s item_count=%s total=%s", user_id, summary["item_count"], summary["total"])
        return jsonify(cart=summary)


@app.post("/cart/items")
def add_item():
    body = request.get_json(silent=True) or {}
    user_id = body.get("user_id", "u100")
    product_id = body.get("product_id")
    quantity = int(body.get("quantity", 1))
    with tracer.start_as_current_span("cart_add_item"):
        simulate("/cart/items")
        if product_id not in PRODUCTS:
            return jsonify(error="product_not_found", product_id=product_id), 404
        cart = read_cart(user_id)
        cart[product_id] = cart.get(product_id, 0) + quantity
        write_cart(user_id, cart)
        summary = summarize(cart)
        logger.info("cart item added user_id=%s product_id=%s total=%s", user_id, product_id, summary["total"])
        return jsonify(cart=summary), 201


@app.delete("/cart/items/<product_id>")
def remove_item(product_id):
    user_id = request.args.get("user_id", "u100")
    with tracer.start_as_current_span("cart_remove_item"):
        simulate("/cart/items/<product_id>")
        cart = read_cart(user_id)
        if product_id not in cart:
            return jsonify(error="item_not_in_cart", product_id=product_id), 404
        del cart[product_id]
        write_cart(user_id, cart)
        summary = summarize(cart)
        logger.info("cart item removed user_id=%s product_id=%s total=%s", user_id, product_id, summary["total"])
        return jsonify(cart=summary)


@app.post("/cart/clear")
def clear_cart():
    body = request.get_json(silent=True) or {}
    user_id = body.get("user_id", "u100")
    with tracer.start_as_current_span("cart_clear"):
        simulate("/cart/clear")
        write_cart(user_id, {})
        logger.info("cart cleared user_id=%s", user_id)
        return jsonify(cart=summarize({}))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
