from flask import Flask, request, jsonify
import openai
import requests
import os

app = Flask(__name__)

# Load environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")
slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

@app.route("/", methods=["GET"])
def health_check():
    return "Fathom-GPT-Slack webhook is live!"

@app.route("/fathom-webhook", methods=["POST"])
def handle_fathom():
    try:
        # Log headers and raw request
        print("🚨 Headers:", dict(request.headers))
        print("🚨 Raw data (bytes):", request.data)

        try:
            body_str = request.data.decode('utf-8')
            print("🚨 Raw data (decoded):", body_str)
        except Exception as decode_err:
            print("❌ Decode error:", decode_err)

        data = request.get_json(force=True)
        print("✅ Parsed JSON:", data)

        # Extract values
        transcript = data.get("transcript", "").strip()
        meeting_title = data.get("meeting_title", "Untitled Meeting").strip()

        print(f"📝 Transcript: {transcript}")
        print(f"📝 Meeting Title: {meeting_title}")

        if not transcript:
            print("❌ Error: Transcript is missing or empty!")
            return jsonify({"error": "Transcript required"}), 400

        print("✅ Transcript check passed. Calling GPT...")

        # Call GPT
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

        # Send to Slack
        slack_payload = {
            "text": f"*📋 {meeting_title}*\n\n```{summary}```"
        }

        slack_response = requests.post(slack_webhook, json=slack_payload)

        if slack_response.status_code != 200:
            print("⚠️ Slack post failed:", slack_response.text)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("❌ Exception occurred:", str(e))
        return jsonify({"error": "Internal server error"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
