import os
from urllib.parse import urlencode

import requests
from flask import Flask, jsonify, redirect, render_template, request, url_for

from common.observability import setup_observability


SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "frontend")
USER_URL = os.getenv("USER_API_URL", "http://user-api:8080")
CART_URL = os.getenv("CART_API_URL", "http://cart-api:8080")
ORDERS_URL = os.getenv("ORDERS_API_URL", "http://orders-api:8080")
PAYMENT_URL = os.getenv("PAYMENT_API_URL", "http://payment-api:8080")
SHIPPING_URL = os.getenv("SHIPPING_API_URL", "http://shipping-api:8080")
DEMO_USER_ID = os.getenv("DEMO_USER_ID", "u100")

app = Flask(__name__)
logger, tracer, simulate = setup_observability(app, SERVICE_NAME)


PRODUCT_DETAILS = {
    "p100": {"tag": "Travel", "accent": "green", "summary": "Weather-ready storage for commutes and weekend trips."},
    "p200": {"tag": "Desk", "accent": "blue", "summary": "Compact wireless control for focused everyday work."},
    "p300": {"tag": "Power", "accent": "amber", "summary": "One compact hub for displays, charging, and accessories."},
    "p400": {"tag": "Audio", "accent": "coral", "summary": "Quiet listening with a soft over-ear fit."},
}


def get_json(url, fallback=None):
    try:
        response = requests.get(url, timeout=3)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.warning("frontend dependency unavailable url=%s error=%s", url, exc)
        return fallback if fallback is not None else {}


def post_json(url, payload):
    response = requests.post(url, json=payload, timeout=4)
    response.raise_for_status()
    return response.json()


def delete_json(url):
    response = requests.delete(url, timeout=4)
    response.raise_for_status()
    return response.json()


def redirect_home(**params):
    query = urlencode({key: value for key, value in params.items() if value})
    target = url_for("home")
    if query:
        target = f"{target}?{query}"
    return redirect(target)


def service_status(name, url):
    try:
        response = requests.get(f"{url}/healthz", timeout=2)
        response.raise_for_status()
        return {"name": name, "state": "Online", "ok": True}
    except Exception:
        return {"name": name, "state": "Check", "ok": False}


def load_shop_state():
    products_payload = get_json(f"{ORDERS_URL}/products", {"products": []})
    products = []
    for product in products_payload.get("products", []):
        details = PRODUCT_DETAILS.get(product.get("id"), {})
        products.append({**product, **details})

    cart_payload = get_json(f"{CART_URL}/cart/{DEMO_USER_ID}", {"cart": {"items": [], "item_count": 0, "total": 0}})
    user = get_json(f"{USER_URL}/users/{DEMO_USER_ID}", {"id": DEMO_USER_ID, "name": "Demo Shopper", "tier": "guest"})
    services = [
        service_status("Frontend", "http://localhost:8080"),
        service_status("Orders", ORDERS_URL),
        service_status("Cart", CART_URL),
        service_status("Payments", PAYMENT_URL),
        service_status("Shipping", SHIPPING_URL),
    ]

    return {
        "products": products,
        "cart": cart_payload.get("cart", {"items": [], "item_count": 0, "total": 0}),
        "user": user,
        "services": services,
    }


@app.get("/")
def home():
    with tracer.start_as_current_span("render_storefront"):
        simulate("/")
        state = load_shop_state()
        logger.info(
            "frontend page rendered user_id=%s product_count=%s cart_items=%s",
            DEMO_USER_ID,
            len(state["products"]),
            state["cart"].get("item_count", 0),
        )
        return render_template(
            "index.html",
            products=state["products"],
            cart=state["cart"],
            cart_items=state["cart"].get("items", []),
            user=state["user"],
            services=state["services"],
            notice=request.args.get("notice"),
            error=request.args.get("error"),
            checkout_id=request.args.get("checkout_id"),
            payment_id=request.args.get("payment_id"),
            shipment_id=request.args.get("shipment_id"),
        )


@app.get("/home")
def shopping_home():
    with tracer.start_as_current_span("render_home"):
        simulate("/home")
        state = load_shop_state()
        logger.info("frontend home data rendered user_id=%s product_count=%s", DEMO_USER_ID, len(state["products"]))
        return jsonify(user=state["user"], products=state["products"], cart=state["cart"])


@app.post("/cart/items")
def add_cart_item():
    product_id = request.form.get("product_id", "")
    quantity = int(request.form.get("quantity", "1") or "1")
    if quantity < 1:
        return redirect_home(error="Quantity must be at least 1")

    with tracer.start_as_current_span("frontend_add_cart_item"):
        simulate("/cart/items")
        try:
            post_json(f"{CART_URL}/cart/items", {"user_id": DEMO_USER_ID, "product_id": product_id, "quantity": quantity})
            logger.info("frontend cart item added product_id=%s quantity=%s", product_id, quantity)
            return redirect_home(notice="Added item to cart")
        except Exception as exc:
            logger.warning("frontend cart add failed product_id=%s error=%s", product_id, exc)
            return redirect_home(error="Could not add item to cart")


@app.post("/cart/remove")
def remove_cart_item():
    product_id = request.form.get("product_id", "")
    with tracer.start_as_current_span("frontend_remove_cart_item"):
        simulate("/cart/remove")
        try:
            delete_json(f"{CART_URL}/cart/items/{product_id}?user_id={DEMO_USER_ID}")
            logger.info("frontend cart item removed product_id=%s", product_id)
            return redirect_home(notice="Removed item from cart")
        except Exception as exc:
            logger.warning("frontend cart remove failed product_id=%s error=%s", product_id, exc)
            return redirect_home(error="Could not remove item")


@app.post("/cart/clear")
def clear_cart():
    with tracer.start_as_current_span("frontend_clear_cart"):
        simulate("/cart/clear")
        try:
            post_json(f"{CART_URL}/cart/clear", {"user_id": DEMO_USER_ID})
            logger.info("frontend cart cleared")
            return redirect_home(notice="Cart cleared")
        except Exception as exc:
            logger.warning("frontend cart clear failed error=%s", exc)
            return redirect_home(error="Could not clear cart")


@app.post("/checkout")
def checkout():
    with tracer.start_as_current_span("frontend_checkout"):
        simulate("/checkout")
        state = load_shop_state()
        cart = state["cart"]
        total = float(cart.get("total", 0))
        if total <= 0:
            return redirect_home(error="Cart is empty")

        try:
            payment = post_json(f"{PAYMENT_URL}/payments", {"user_id": DEMO_USER_ID, "amount": total}).get("payment", {})
            shipment = post_json(f"{SHIPPING_URL}/shipments", {"order_id": payment.get("id", "order-demo")}).get("shipment", {})
            post_json(f"{CART_URL}/cart/clear", {"user_id": DEMO_USER_ID})
            logger.info(
                "frontend checkout completed payment_id=%s shipment_id=%s total=%s",
                payment.get("id"),
                shipment.get("id"),
                total,
            )
            return redirect_home(
                notice="Checkout complete",
                checkout_id="order-demo",
                payment_id=payment.get("id"),
                shipment_id=shipment.get("id"),
            )
        except Exception as exc:
            logger.warning("frontend checkout failed error=%s", exc)
            return redirect_home(error="Checkout failed")


@app.get("/checkout-demo")
def checkout_demo():
    with tracer.start_as_current_span("checkout_demo"):
        simulate("/checkout-demo")
        cart = requests.post(
            f"{CART_URL}/cart/items",
            json={"user_id": DEMO_USER_ID, "product_id": "p100", "quantity": 1},
            timeout=3,
        ).json()
        payment = requests.post(
            f"{PAYMENT_URL}/payments",
            json={"user_id": DEMO_USER_ID, "amount": cart.get("cart", {}).get("total", 49.99)},
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
