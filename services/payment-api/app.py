import os
import random
import uuid

from flask import Flask, jsonify, request

from common.observability import setup_observability


SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "payment-api")
app = Flask(__name__)
logger, tracer, simulate = setup_observability(app, SERVICE_NAME)


@app.get("/")
def home():
    return {"service": SERVICE_NAME, "endpoints": ["POST /payments", "/metrics", "/healthz"]}


@app.post("/payments")
def create_payment():
    body = request.get_json(silent=True) or {}
    amount = float(body.get("amount", 0))
    user_id = body.get("user_id", "u100")
    with tracer.start_as_current_span("authorize_payment"):
        simulate("/payments")
        if amount <= 0:
            return jsonify(error="invalid_amount"), 400
        if random.random() < 0.05:
            logger.warning("payment declined user_id=%s amount=%s", user_id, amount)
            return jsonify(error="payment_declined"), 402
        payment = {"id": f"pay-{uuid.uuid4().hex[:8]}", "status": "authorized", "amount": amount, "user_id": user_id}
        logger.info("payment authorized payment_id=%s user_id=%s amount=%s", payment["id"], user_id, amount)
        return jsonify(payment=payment), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
