from flask import Flask, request, jsonify
import openai
import requests
import os

app = Flask(__name__)

# Load keys from environment
openai.api_key = os.getenv("OPENAI_API_KEY")
slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

@app.route("/", methods=["GET"])
def health_check():
    return "Fathom-GPT-Slack webhook is live!"

@app.route("/fathom-webhook", methods=["POST"])
def handle_fathom():
    try:
        # Log headers and raw request data
        print("🚨 Headers:", dict(request.headers))
        print("🚨 Raw data:", request.data)

        # Parse JSON payload
        data = request.get_json(force=True)
        print("✅ Parsed JSON:", data)

        transcript = data.get("transcript", "").strip()
        meeting_title = data.get("meeting_title", "Untitled Meeting").strip()

        # Validate required fields
        if not transcript:
            print("❌ Error: Transcript is missing or empty!")
            return jsonify({"error": "Transcript required"}), 400

        # Call OpenAI GPT
        print("🤖 Calling GPT with transcript...")
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Summarize this meeting and extract clear dev epics and user stories. Format output in Slack Markdown."
                },
                {
                    "role": "user",
                    "content": transcript
                }
            ],
            temperature=0.3
        )

        summary = response['choices'][0]['message']['content']
        print("✅ GPT summary generated.")

        # Send summary to Slack
        slack_payload = {
            "text": f"*📋 {meeting_title}*\n\n```{summary}```"
        }
        slack_response = requests.post(slack_webhook, json=slack_payload)

        if slack_response.status_code != 200:
            print("⚠️ Slack post failed:", slack_response.text)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("❌ Exception occurred:", str(e))
        return jsonify({"error": "Invalid request"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
