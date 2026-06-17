import os

import requests
from flask import Flask, jsonify

from common.observability import setup_observability


SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "frontend")
USER_URL = os.getenv("USER_API_URL", "http://user-api:8080")
CART_URL = os.getenv("CART_API_URL", "http://cart-api:8080")
ORDERS_URL = os.getenv("ORDERS_API_URL", "http://orders-api:8080")
PAYMENT_URL = os.getenv("PAYMENT_API_URL", "http://payment-api:8080")
SHIPPING_URL = os.getenv("SHIPPING_API_URL", "http://shipping-api:8080")

app = Flask(__name__)
logger, tracer, simulate = setup_observability(app, SERVICE_NAME)


def get_json(url):
    response = requests.get(url, timeout=3)
    response.raise_for_status()
    return response.json()


@app.get("/")
def home():
    return jsonify(
        service=SERVICE_NAME,
        message="Shopping platform frontend",
        pages=["/home", "/checkout-demo", "/healthz", "/metrics"],
    )


@app.get("/home")
def shopping_home():
    with tracer.start_as_current_span("render_home"):
        simulate("/home")
        products = get_json(f"{ORDERS_URL}/products")
        user = get_json(f"{USER_URL}/users/u100")
        logger.info("frontend home rendered user_id=u100 product_count=%s", len(products.get("products", [])))
        return jsonify(user=user, products=products.get("products", []))


@app.get("/checkout-demo")
def checkout_demo():
    with tracer.start_as_current_span("checkout_demo"):
        simulate("/checkout-demo")
        cart = requests.post(
            f"{CART_URL}/cart/items",
            json={"product_id": "p100", "quantity": 1},
            timeout=3,
        ).json()
        payment = requests.post(
            f"{PAYMENT_URL}/payments",
            json={"user_id": "u100", "amount": cart.get("cart", {}).get("total", 49.99)},
            timeout=3,
        ).json()
        shipping = requests.post(
            f"{SHIPPING_URL}/shipments",
            json={"order_id": payment.get("payment", {}).get("id", "pay-demo")},
            timeout=3,
        ).json()
        logger.info("frontend checkout demo completed payment=%s", payment.get("payment", {}).get("id"))
        return jsonify(cart=cart, payment=payment, shipping=shipping)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
