import os
import logging
from flask import Flask, jsonify, request

app = Flask(__name__)
POD_NAME = os.environ.get("POD_NAME", "unknown-pod")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
# hide the default Flask request logs, we print our own line
logging.getLogger("werkzeug").setLevel(logging.ERROR)

stock = {"apple": 10, "banana": 5, "laptop": 2}


@app.after_request
def log_request(response):
    logging.info("pod=%s endpoint=%s status=%s", POD_NAME, request.path, response.status_code)
    return response


@app.route("/inventory/<item_id>")
def get_item(item_id):
    if item_id not in stock:
        return jsonify({"item": item_id, "error": "not found", "pod": POD_NAME}), 404
    return jsonify({"item": item_id, "stock": stock[item_id], "pod": POD_NAME})


@app.route("/ready")
def ready():
    if os.path.exists("/tmp/not-ready"):
        return jsonify({"ready": False, "pod": POD_NAME}), 503
    return jsonify({"ready": True, "pod": POD_NAME})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "pod": POD_NAME})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
