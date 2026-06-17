import os
import uuid

from flask import Flask, jsonify, request

from common.observability import setup_observability


SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "shipping-api")
app = Flask(__name__)
logger, tracer, simulate = setup_observability(app, SERVICE_NAME)


@app.get("/")
def home():
    return {"service": SERVICE_NAME, "endpoints": ["POST /shipments", "/metrics", "/healthz"]}


@app.post("/shipments")
def create_shipment():
    body = request.get_json(silent=True) or {}
    order_id = body.get("order_id", "ord-demo")
    with tracer.start_as_current_span("create_shipment"):
        simulate("/shipments")
        shipment = {
            "id": f"ship-{uuid.uuid4().hex[:8]}",
            "order_id": order_id,
            "status": "label_created",
            "carrier": "demo-express",
        }
        logger.info("shipment created shipment_id=%s order_id=%s", shipment["id"], order_id)
        return jsonify(shipment=shipment), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
