from flask import Flask, request, jsonify
from openai import OpenAI
import requests
import os
import json
import re

app = Flask(__name__)

# Initialize clients and environment variables
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
slack_token = os.getenv("SLACK_BOT_TOKEN")
slack_channel_id = "C098402A8KF"

# Constants
GPT_MODEL = "gpt-4o"
GPT_PROMPT = (
    "You are a senior product manager and agile coach. Your task is to convert a meeting transcript "
    "into clear, structured development documentation.\n\n"
    "First, provide a concise summary of key themes discussed in the meeting.\n\n"
    "Then, for each major topic, extract:\n\n"
    "1. Problem Statement\n"
    "Briefly explain the core problem or opportunity this work is addressing.\n\n"
    "2. Description\n"
    "Summarize the context, scope, and any relevant background details needed for designers and developers to understand the feature or task.\n\n"
    "3. User Story\n"
    "Use the format:\n“As a [type of user], I want [feature or behavior] so that [user benefit or value].”\n\n"
    "4. Acceptance Criteria\n"
    "List specific, numbered criteria that must be met for the story to be considered complete. Use a clear and testable format.\n\n"
    "Be concise, structured, and audience-aware — this will be read by product, design, and engineering stakeholders."
)

ZERO_WIDTH_CHARACTERS = r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]"

@app.route("/", methods=["GET"])
def health_check():
    return "✅ Fathom-GPT-Slack webhook is live!"

@app.route("/fathom-webhook", methods=["POST"])
def handle_fathom_webhook():
    try:
        # Read and clean raw body
        raw_body = request.data.decode("utf-8", errors="replace").strip()
        print("🚨 Raw body string:\n", raw_body)

        cleaned_body = re.sub(ZERO_WIDTH_CHARACTERS, "", raw_body)

        try:
            payload = json.loads(cleaned_body)
        except json.JSONDecodeError as e:
            print("❌ JSON decode error:", e)
            return jsonify({"error": "Invalid JSON"}), 400

        transcript = payload.get("transcript", "").strip()
        meeting_title = payload.get("meeting_title", "Untitled Meeting").strip()

        if not transcript:
            return jsonify({"error": "Transcript is required"}), 400

        print(f"📝 Meeting Title: {meeting_title}")
        print(f"📝 Transcript Preview: {transcript[:200]}...")

        # Send prompt to GPT
        gpt_response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": GPT_PROMPT},
                {"role": "user", "content": transcript}
            ],
            temperature=0.3
        )

        summary = gpt_response.choices[0].message.content
        print("✅ GPT Summary Output:\n", summary)

        # Format and post to Slack
        slack_payload = {
            "channel": slack_channel_id,
            "text": f"*📋 {meeting_title}*\n\n```{summary}```"
        }

        slack_headers = {
            "Authorization": f"Bearer {slack_token}",
            "Content-Type": "application/json"
        }

        slack_response = requests.post(
            "https://slack.com/api/chat.postMessage",
            json=slack_payload,
            headers=slack_headers
        )

        if slack_response.status_code != 200 or not slack_response.json().get("ok"):
            print("⚠️ Slack API error:", slack_response.text)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("❌ Unexpected error:", e)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
