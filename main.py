from flask import Flask, request, jsonify
import openai
import requests
import os

app = Flask(__name__)

@app.route("/fathom-webhook", methods=["POST"])
def handle_fathom():
    try:
        print("🚨 Headers:", dict(request.headers))
        print("🚨 Raw data (bytes):", request.data)

        try:
            body_str = request.data.decode('utf-8')
            print("🚨 Raw data (decoded):", body_str)
        except Exception as decode_err:
            print("❌ Could not decode body:", decode_err)

        data = request.get_json(force=True)
        print("✅ Parsed JSON:", data)

        transcript = data.get("transcript", "").strip()
        meeting_title = data.get("meeting_title", "Untitled Meeting").strip()

        if not transcript:
            print("❌ Error: Transcript is missing or empty!")
            return jsonify({"error": "Transcript required"}), 400

        # GPT and Slack logic (omit for now)
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("❌ Exception:", str(e))
        return jsonify({"error": "Invalid request"}), 400
