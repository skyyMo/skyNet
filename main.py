from flask import Flask, request, jsonify
from openai import OpenAI
import requests
import os
import json
import re

app = Flask(__name__)

# Load environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
slack_token = os.getenv("SLACK_BOT_TOKEN")
channel_id = os.getenv("SLACK_CHANNEL_ID")

jira_domain = os.getenv("JIRA_DOMAIN")
jira_email = os.getenv("JIRA_EMAIL")
jira_api_token = os.getenv("JIRA_API_TOKEN")
jira_project_key = os.getenv("JIRA_PROJECT_KEY")

# GPT system prompt
system_prompt = (
    "You are a senior product manager helping turn meeting transcripts into clear, actionable Jira tickets. "
    "Your goal is to identify the key product areas discussed, extract well-formed user stories using the format: "
    "“As a [user], I want [feature] so that [benefit]”, and define strong acceptance criteria in a numbered list. "
    "Group stories by Epic if possible. Provide story titles that are concise and descriptive."
)

def create_jira_ticket(title, description):
    url = f"https://{jira_domain}/rest/api/3/issue"
    auth = (jira_email, jira_api_token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "fields": {
            "project": {"key": jira_project_key},
            "summary": title,
            "description": description,
            "issuetype": {"name": "Task"}
        }
    }
    response = requests.post(url, headers=headers, auth=auth, json=payload)
    if response.status_code == 201:
        issue_key = response.json().get("key")
        print(f"✅ Created Jira issue: {issue_key}")
        return issue_key
    else:
        print(f"❌ Jira error: {response.text}")
        return None

@app.route("/", methods=["GET"])
def health_check():
    return "Fathom-GPT-JIRA-Slack webhook is live!"

@app.route("/fathom-webhook", methods=["POST"])
def handle_fathom():
    try:
        raw_data = request.data.decode("utf-8", errors="replace").strip()
        print("🚨 Raw body string:\n", raw_data)

        # Clean potential hidden characters
        cleaned_data = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]", "", raw_data)
        data = json.loads(cleaned_data)

        # Safely extract fields
        transcript = str(data.get("transcript", "")).strip()
        meeting_title = str(data.get("meeting_title", "Untitled Meeting")).strip()

        print("📦 Transcript Raw:", data.get("transcript"))
        print("📦 Title Raw:", data.get("meeting_title"))

        if not transcript:
            return jsonify({"error": "Transcript required"}), 400

        print(f"📝 Title: {meeting_title}")
        print(f"📝 Transcript Preview: {transcript[:200]}...")

        # GPT call
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

        # Extract user stories
        stories = re.findall(r"\*\*Title:\*\* (.*?)\nStory: (.*?)\nAcceptance Criteria:(.*?)\n(?=\*\*Title:|$)", summary, re.DOTALL)
        jira_links = []

        for title, story, criteria in stories:
            description = f"{story.strip()}\n\n*Acceptance Criteria:*\n{criteria.strip()}"
            issue_key = create_jira_ticket(title.strip(), description)
            if issue_key:
                jira_links.append(f"- <https://{jira_domain}/browse/{issue_key}|{issue_key}: {title.strip()}>")

        # Slack message
        if jira_links:
            slack_message = f"*📋 {meeting_title} — {len(jira_links)} stories created:*\n" + "\n".join(jira_links)
        else:
            slack_message = f"*📋 {meeting_title} — No stories were created from this transcript.*"

        slack_payload = {"channel": channel_id, "text": slack_message}
        headers = {
            "Authorization": f"Bearer {slack_token}",
            "Content-Type": "application/json"
        }

        slack_response = requests.post("https://slack.com/api/chat.postMessage", json=slack_payload, headers=headers)
        if slack_response.status_code != 200 or not slack_response.json().get("ok"):
            print("⚠️ Slack error:", slack_response.text)

        return jsonify({"status": "success", "stories_created": len(jira_links)}), 200

    except json.JSONDecodeError as e:
        print("❌ JSON decode failed:", str(e))
        return jsonify({"error": "Invalid JSON"}), 400
    except Exception as e:
        print("❌ Unexpected exception:", str(e))
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
