from flask import Flask, request, jsonify
from openai import OpenAI
from requests.auth import HTTPBasicAuth
import requests
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# 🔑 API Clients & Secrets
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
slack_token = os.getenv("SLACK_BOT_TOKEN")
slack_channel_id = os.getenv("SLACK_CHANNEL_ID")
jira_domain = os.getenv("JIRA_DOMAIN")
jira_email = os.getenv("JIRA_EMAIL")
jira_token = os.getenv("JIRA_API_TOKEN")
jira_project = os.getenv("JIRA_PROJECT_KEY")

# 🧠 Inline GPT Prompt
GPT_PROMPT = """
You are a senior product manager and agile coach. Your task is to convert a meeting transcript into clear, structured development documentation.

First, provide a concise summary of key themes discussed in the meeting.

Then, for each major topic, extract:

1. Problem Statement
Briefly explain the core problem or opportunity this work is addressing.

2. Description
Summarize the context, scope, and any relevant background details needed for designers and developers to understand the feature or task.

3. User Story
Use the format:
“As a [type of user], I want [feature or behavior] so that [user benefit or value].”

4. Acceptance Criteria
List specific, numbered criteria that must be met for the story to be considered complete. Use a clear and testable format.

Be concise, structured, and audience-aware — this will be read by product, design, and engineering stakeholders.
"""

ZERO_WIDTH_CHARS = r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]"

@app.route("/", methods=["GET"])
def health_check():
    return "✅ Fathom-GPT-Jira webhook is live!"

@app.route("/fathom-webhook", methods=["POST"])
def handle_fathom():
    try:
        raw_data = request.data.decode("utf-8", errors="replace").strip()
        cleaned = re.sub(ZERO_WIDTH_CHARS, "", raw_data)

        try:
            payload = json.loads(cleaned)
        except Exception as e:
            return jsonify({"error": "Invalid JSON"}), 400

        transcript = payload.get("transcript", "").strip()
        title = payload.get("meeting_title", "Untitled Meeting").strip()
        if not transcript:
            return jsonify({"error": "Transcript required"}), 400

        # 🧠 Generate structured story summary with GPT
        gpt_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": GPT_PROMPT},
                {"role": "user", "content": transcript}
            ],
            temperature=0.3
        )
        summary = gpt_response.choices[0].message.content

        # 💬 Post summary to Slack
        slack_payload = {
            "channel": slack_channel_id,
            "text": f"*📋 {title}*\n\n```{summary}```"
        }
        slack_headers = {
            "Authorization": f"Bearer {slack_token}",
            "Content-Type": "application/json"
        }
        slack_response = requests.post("https://slack.com/api/chat.postMessage", json=slack_payload, headers=slack_headers)
        if slack_response.status_code != 200 or not slack_response.json().get("ok"):
            print("⚠️ Slack error:", slack_response.text)

        # 🧾 Parse and create Jira tickets
        tickets = parse_gpt_summary(summary)
        for ticket in tickets:
            create_jira_issue(ticket["summary"], ticket["description"])

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("❌ Exception:", str(e))
        return jsonify({"error": "Internal server error"}), 500

def parse_gpt_summary(gpt_text):
    sections = re.split(r"\n+---+\n+", gpt_text)
    tickets = []

    for section in sections:
        if not section.strip():
            continue

        title_match = re.search(r"\*\*\d+\.\s+(.*?)\*\*", section)
        summary = title_match.group(1).strip() if title_match else "Untitled"

        prob = re.search(r"\*\*Problem Statement:\*\*\s+(.*?)(?:\n|$)", section, re.DOTALL)
        desc = re.search(r"\*\*Description:\*\*\s+(.*?)(?:\n|$)", section, re.DOTALL)
        user_story = re.search(r"\*\*User Story:\*\*\s+(.*?)(?:\n|$)", section, re.DOTALL)
        ac = re.search(r"\*\*Acceptance Criteria:\*\*\s+(.+)", section, re.DOTALL)

        description = ""
        if prob: description += f"*Problem Statement:*\n{prob.group(1).strip()}\n\n"
        if desc: description += f"*Description:*\n{desc.group(1).strip()}\n\n"
        if user_story: description += f"*User Story:*\n{user_story.group(1).strip()}\n\n"
        if ac:
            ac_lines = re.findall(r"\d+\.\s+.*", ac.group(1).strip())
            description += "*Acceptance Criteria:*\n" + "\n".join(f"- {line}" for line in ac_lines)

        tickets.append({"summary": summary, "description": description})

    return tickets

def create_jira_issue(summary, description):
    url = f"https://{jira_domain}/rest/api/3/issue"
    auth = HTTPBasicAuth(jira_email, jira_token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = {
        "fields": {
            "project": {"key": jira_project},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Story"}
        }
    }

    res = requests.post(url, headers=headers, auth=auth, json=payload)
    if res.status_code == 201:
        issue_key = res.json()["key"]
        print(f"✅ Created: {issue_key} - {summary}")

        # 📨 Slack Jira link
        slack_payload = {
            "channel": slack_channel_id,
            "text": f"📌 *New Jira Story Created:* <https://{jira_domain}/browse/{issue_key}|{issue_key}> – {summary}"
        }
        slack_headers = {
            "Authorization": f"Bearer {slack_token}",
            "Content-Type": "application/json"
        }
        slack_response = requests.post("https://slack.com/api/chat.postMessage", json=slack_payload, headers=slack_headers)
        if slack_response.status_code != 200 or not slack_response.json().get("ok"):
            print("⚠️ Slack Jira link failed:", slack_response.text)
    else:
        print(f"❌ Jira create failed: {summary} | {res.status_code} | {res.text}")
