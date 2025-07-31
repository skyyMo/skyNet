from flask import Flask, request, jsonify
from openai import OpenAI
import requests
import os

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
slack_token = os.getenv("SLACK_BOT_TOKEN")
channel_id = "C098402A8KF"

@app.route("/", methods=["GET"])
def health_check():
    return "Fathom-GPT-Slack webhook is live!"

@app.route("/fathom-webhook", methods=["POST"])
def handle_fathom():
    try:
        raw_data = request.data.decode("utf-8", errors="replace").strip()
        print("🚨 Raw body:\n", raw_data)

        try:
            data = request.get_json(force=True)
        except Exception as e:
            print("❌ JSON decode error:", str(e))
            return jsonify({"error": "Invalid JSON payload"}), 400

        transcript = data.get("transcript", "").strip()
        meeting_title = data.get("meeting_title", "Untitled Meeting").strip()

        if not transcript:
            return jsonify({"error": "Transcript required"}), 400

        print(f"📝 Title: {meeting_title}")
        print(f"📝 Transcript Preview: {transcript[:200]}...")

        # GPT processing
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a senior product manager and agile coach helping to convert meeting transcripts into clear, actionable development specs.\n\nSummarize the key themes of the meeting, then extract:\n1. High-level epics\n2. Detailed user stories using the format: “As a [user], I want [feature] so that [benefit]”\n3. Acceptance criteria for each story using numbered scope that's important to complete and easy to understand.\n\nBe concise, structured, and assume an audience of designers and developers."},
                {"role": "user", "content": transcript}
            ],
            temperature=0.3
        )

        summary = response.choices[0].message.content
        print("✅ GPT Summary Output:\n", summary)

        # Post to Slack
        slack_payload = {
            "channel": channel_id,
            "text": f"*📋 {meeting_title}*\n\n```{summary}```"
        }

        headers = {
            "Authorization": f"Bearer {slack_token}",
            "Content-Type": "application/json"
        }

        slack_response = requests.post("https://slack.com/api/chat.postMessage", json=slack_payload, headers=headers)

        if slack_response.status_code != 200 or not slack_response.json().get("ok"):
            print("⚠️ Slack error:", slack_response.text)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("❌ Unexpected exception:", str(e))
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
