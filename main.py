from flask import Flask, request, jsonify
from openai import OpenAI
import requests
import os
import json
import re

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
        print("🚨 Raw body string:\n", raw_data)

        # Remove invisible control characters (e.g., zero-width spaces)
        cleaned_data = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]", "", raw_data)

        try:
            data = json.loads(cleaned_data)
        except Exception as e:
            print("❌ JSON manual decode failed:", str(e))
            return jsonify({"error": "Invalid JSON"}), 400

        transcript = data.get("transcript", "").strip()
        meeting_title = data.get("meeting_title", "Untitled Meeting").strip()

        if not transcript:
            return jsonify({"error": "Transcript required"}), 400

        print(f"📝 Title: {meeting_title}")
        print(f"📝 Transcript Preview: {transcript[:200]}...")

        # 🧠 GPT prompt tailored for OddsShopper's PortfolioEV and Tails
        system_prompt = (
            "You are a senior product manager at OddsShopper working on two product lines: "
            "PortfolioEV (a tool that helps sports bettors build diversified, profitable bet portfolios) "
            "and Tails (a platform for discovering and following betting experts). Your job is to analyze "
            "meeting transcripts and output high-quality product documentation.\n\n"
            "Start by summarizing the key themes discussed in the meeting. Then extract:\n\n"
            "1. **Epics** — clearly defined problem-solution groupings tied to sports bettor pain points\n"
            "2. **User Stories** — using the format: 'As a [user], I want [feature] so that [benefit]'\n"
            "3. **Story Titles** — short, actionable labels for each story (no duplicates)\n"
            "4. **Acceptance Criteria** — concise, numbered lists of what success looks like\n\n"
            "Avoid duplicate text. Do not repeat the same story or criteria multiple times. Tailor your output "
            "to real challenges bettors might face, like bankroll stress, app confusion, retention issues, or unclear value."
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            temperature=0.3
        )

        summary = response.choices[0].message.content
        print("✅ GPT Summary Output:\n", summary)

        # 📬 Post to Slack
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
