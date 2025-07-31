from flask import Flask, request, jsonify
from openai import OpenAI
import requests
import os
from notion_client import Client as NotionClient

app = Flask(__name__)

# Load environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
slack_token = os.getenv("SLACK_BOT_TOKEN")
notion_token = os.getenv("NOTION_TOKEN")
channel_id = "C098402A8KF"  # Your Slack channel ID
webhook_url = os.getenv("WEBHOOK_URL") or "https://skynet-72b6.onrender.com/fathom-webhook"

# Initialize Notion client
notion = NotionClient(auth=notion_token)

@app.route("/fathom-webhook", methods=["POST"])
def handle_fathom():
    # 🐛 Debug logs
    print("🚨 HEADERS:", dict(request.headers))
    try:
        print("🚨 RAW BODY:", request.data.decode('utf-8'))
    except Exception as decode_err:
        print("❌ Decode error:", decode_err)

    try:
        data = request.get_json(force=True)
        print("✅ Parsed JSON:", data)

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

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a senior product manager and agile coach helping to convert meeting transcripts into clear, actionable development specs.

Summarize the key themes of the meeting, then extract:
1. High-level epics
2. Detailed user stories using the format: “As a [user], I want [feature] so that [benefit]”
3. Acceptance criteria for each story using numbered scope that's important to complete and easy to understand.

Use clean formatting, group related stories together, and ensure everything is clear enough for an engineer to begin implementation with minimal follow-up.

Be concise, structured, and assume an audience of designers and developers."""
                },
                {
                    "role": "user",
                    "content": transcript
                }
            ],
            temperature=0.3
        )

        summary = response.choices[0].message.content
        print("✅ GPT summary generated.")

        slack_payload = {
            "channel": channel_id,
            "text": f"*📋 {meeting_title}*\n\n```{summary}```"
        }

        headers = {
            "Authorization": f"Bearer {slack_token}",
            "Content-Type": "application/json"
        }

        slack_response = requests.post(
            "https://slack.com/api/chat.postMessage",
            json=slack_payload,
            headers=headers
        )

        if slack_response.status_code != 200 or not slack_response.json().get("ok"):
            print("⚠️ Slack post failed:", slack_response.text)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("❌ Exception occurred:", str(e))
        return jsonify({"error": "Internal server error"}), 400


@app.route("/notion-transcript", methods=["POST"])
def notion_transcript():
    data = request.get_json()
    page_id = data.get("page_id")
    meeting_title = data.get("meeting_title", "Untitled Meeting")

    if not page_id:
        return jsonify({"error": "Missing Notion page_id"}), 400

    try:
        blocks = notion.blocks.children.list(page_id)
        transcript = ""

        for block in blocks.get("results", []):
            if block["type"] == "paragraph":
                for rt in block["paragraph"].get("rich_text", []):
                    transcript += rt.get("plain_text", "") + "\n"

        if not transcript.strip():
            return jsonify({"error": "Transcript is empty"}), 400

        payload = {
            "transcript": transcript.strip(),
            "meeting_title": meeting_title
        }

        webhook_response = requests.post(webhook_url, json=payload)

        if webhook_response.status_code != 200:
            print("⚠️ Webhook failed:", webhook_response.text)
            return jsonify({"error": "Webhook call failed"}), 500

        return jsonify({"status": "Notion transcript sent to GPT"}), 200

    except Exception as e:
        print("❌ Error with Notion fetch:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
