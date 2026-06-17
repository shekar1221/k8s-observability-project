import os

import pymysql
from flask import Flask, jsonify

from common.observability import setup_observability


SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "user-api")
MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_USER = os.getenv("MYSQL_USER", "shop")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "shop")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "shop")

USERS = {
    "u100": {"id": "u100", "name": "Asha Rao", "tier": "gold", "email": "asha@example.com"},
    "u200": {"id": "u200", "name": "Ravi Kumar", "tier": "silver", "email": "ravi@example.com"},
}

app = Flask(__name__)
logger, tracer, simulate = setup_observability(app, SERVICE_NAME)


def ensure_mysql():
    try:
        conn = pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DATABASE, connect_timeout=2)
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS users (id VARCHAR(32) PRIMARY KEY, name VARCHAR(128), tier VARCHAR(32), email VARCHAR(128))")
            for user in USERS.values():
                cur.execute("REPLACE INTO users (id, name, tier, email) VALUES (%s, %s, %s, %s)", (user["id"], user["name"], user["tier"], user["email"]))
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.warning("mysql unavailable fallback=in_memory error=%s", exc)
        return False


@app.get("/")
def home():
    return {"service": SERVICE_NAME, "endpoints": ["/users", "/users/<user_id>", "/metrics", "/healthz"]}


@app.get("/users")
def list_users():
    with tracer.start_as_current_span("list_users"):
        simulate("/users")
        ensure_mysql()
        logger.info("users listed count=%s", len(USERS))
        return jsonify(users=list(USERS.values()))


@app.get("/users/<user_id>")
def get_user(user_id):
    with tracer.start_as_current_span("get_user"):
        simulate("/users/<user_id>")
        user = USERS.get(user_id)
        if not user:
            logger.warning("user not found user_id=%s", user_id)
            return jsonify(error="user_not_found", user_id=user_id), 404
        logger.info("user loaded user_id=%s tier=%s", user_id, user["tier"])
        return jsonify(user)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
