from flask import Flask, request, jsonify
from openai import OpenAI
import requests
import os

app = Flask(__name__)

# Load environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
slack_token = os.getenv("SLACK_BOT_TOKEN")
channel_id = "C098402A8KF"  # Your target Slack channel ID

@app.route("/", methods=["GET"])
def health_check():
    return "Fathom-GPT-Slack webhook is live!"

@app.route("/fathom-webhook", methods=["POST"])
def handle_fathom():
    try:
        print("🚨 Headers:", dict(request.headers))
        print("🚨 Raw data (bytes):", request.data)

        try:
            body_str = request.data.decode('utf-8')
            print("🚨 Raw data (decoded):", body_str)
        except Exception as decode_err:
            print("❌ Decode error:", decode_err)

        data = request.get_json(force=True)
        print("✅ Parsed JSON:", data)

        transcript = data.get("transcript", "").strip()
        meeting_title = data.get("meeting_title", "Untitled Meeting").strip()

        print(f"📝 Transcript: {transcript}")
        print(f"📝 Meeting Title: {meeting_title}")

        if not transcript:
            print("❌ Error: Transcript is missing or empty!")
            return jsonify({"error": "Transcript required"}), 400

        print("✅ Transcript check passed. Calling GPT...")

        # GPT call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a senior product manager and agile coach helping to convert meeting transcripts into clear, actionable development specs.

Summarize the key themes of the meeting, then extract:
1. High-level epics
2. Detailed user stories using the format: “As a [user], I want [feature] so that [benefit]”
3. Acceptance criteria for each story using Gherkin-style bullets (Given / When / Then)

Use clean formatting, group related stories together, and ensure everything is clear enough for an engineer to begin implementation with minimal follow-up.

Be concise, structured, and assume an audience of designers and developers."""
                },
                {
                    "role": "user",
                    "content": transcript
                }
