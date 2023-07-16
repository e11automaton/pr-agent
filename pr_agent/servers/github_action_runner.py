import asyncio
import json
import os
import re

from pr_agent.config_loader import settings
from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions
from pr_agent.tools.pr_description import PRDescription
from pr_agent.tools.pr_questions import PRQuestions
from pr_agent.tools.pr_reviewer import PRReviewer


async def run_action():
    GITHUB_EVENT_NAME = os.environ.get('GITHUB_EVENT_NAME', None)
    if not GITHUB_EVENT_NAME:
        print("GITHUB_EVENT_NAME not set")
        return
    GITHUB_EVENT_PATH = os.environ.get('GITHUB_EVENT_PATH', None)
    if not GITHUB_EVENT_PATH:
        print("GITHUB_EVENT_PATH not set")
        return
    try:
        event_payload = json.load(open(GITHUB_EVENT_PATH, 'r'))
    except json.decoder.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return
    OPENAI_KEY = os.environ.get('OPENAI_KEY', None)
    if not OPENAI_KEY:
        print("OPENAI_KEY not set")
        return
    OPENAI_ORG = os.environ.get('OPENAI_ORG', None)
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', None)
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not set")
        return
    settings.set("OPENAI.KEY", OPENAI_KEY)
    if OPENAI_ORG:
        settings.set("OPENAI.ORG", OPENAI_ORG)
    settings.set("GITHUB.USER_TOKEN", GITHUB_TOKEN)
    settings.set("GITHUB.DEPLOYMENT_TYPE", "user")
    if GITHUB_EVENT_NAME == "pull_request":
        action = event_payload.get("action", None)
        if action in ["opened", "reopened"]:
            pr_url = event_payload.get("pull_request", {}).get("url", None)
            if pr_url:
                await PRReviewer(pr_url).review()

    elif GITHUB_EVENT_NAME == "issue_comment":
        action = event_payload.get("action", None)
        if action in ["created", "edited"]:
            comment_body = event_payload.get("comment", {}).get("body", None)
            if comment_body:
                pr_url = event_payload.get("issue", {}).get("pull_request", {}).get("url", None)
                if pr_url:
                    body = comment_body.strip().lower()
                    if any(cmd in body for cmd in ["/review", "/review_pr"]):
                        await PRReviewer(pr_url).review()
                    elif any(cmd in body for cmd in ["/describe", "/describe_pr"]):
                        await PRDescription(pr_url).describe()
                    elif any(cmd in body for cmd in ["/improve", "/improve_code"]):
                        await PRCodeSuggestions(pr_url).suggest()
                    elif any(cmd in body for cmd in ["/ask", "/ask_question"]):
                        pattern = r'(/ask|/ask_question)\s*(.*)'
                        matches = re.findall(pattern, comment_body, re.IGNORECASE)
                        if matches:
                            question = matches[0][1]
                            await PRQuestions(pr_url, question).answer()
                    else:
                        print(f"Unknown command: {body}")


if __name__ == '__main__':
    asyncio.run(run_action())