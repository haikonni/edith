#!/usr/bin/env python3
"""Edith Web Server - Flask API (portable)."""
import os
from flask import Flask, render_template, jsonify, request
from edith import Edith

app = Flask(__name__, template_folder="templates")
edith = Edith()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(edith.get_dashboard())


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json or {}
    return jsonify({"response": edith.chat(data.get("message", ""))})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Edith em http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
