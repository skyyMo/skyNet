from flask import Flask, request, jsonify
import traceback

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health_check():
    return "Fathom-GPT-Slack webhook is live!"

@app.route("/fathom-webhook", methods=["POST"])
def handle_fathom():
    try:
        print("🚨 Headers:", dict(request.headers))
        print("🚨 Raw data:", request.data)

        try:
            body_str = request.data.decode('utf-8')
            print("🚨 Decoded body:", body_str)
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

        return jsonify({
            "status": "Webhook received",
            "meeting_title": meeting_title,
            "transcript_preview": transcript[:100] + "..."
        }), 200

    except Exception as e:
        print("❌ Exception occurred:")
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
