from flask import Flask, request, jsonify
import openai
import requests
import os

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

@app.route("/fathom-webhook", methods=["POST"])
def handle_fathom():
    try:
        # Log what's actually coming into the server
        print("🚨 Headers:", dict(request.headers))
        print("🚨 Raw data:", request.data)

        # Try to parse the JSON body
        data = request.get_json(force=True)
        print("✅ Parsed JSON:", data)

        transcript = data.get("transcript")
        meeting_title = data.get("meeting_title", "Untitled Meeting")

        if not transcript:
            print("❌ Error: Transcript missing!")
            return jsonify({"error": "Transcript required"}), 400

        # (Your GPT + Slack logic goes here...)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("❌ Exception occurred:", str(e))
        return jsonify({"error": "Invalid request"}), 400

    data = request.get_json()
    transcript = data.get("transcript", "")

    if not transcript:
        return jsonify({"error": "Transcript missing"}), 400

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Summarize this meeting and extract clear dev epics and user stories. Format output in Slack Markdown."},
                {"role": "user", "content": transcript}
            ],
            temperature=0.3
        )

        summary = completion["choices"][0]["message"]["content"]
        requests.post(slack_webhook, json={"text": summary})

        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def index():
    return "Fathom-GPT-Slack webhook is live!"

if __name__ == "__main__":
    app.run()
