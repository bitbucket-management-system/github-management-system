from datetime import datetime
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

# Load Environment Variables
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_ORG = os.environ.get("GITHUB_ORG", "bitbucket-management-system")
GITHUB_TEAM_SLUG = os.environ.get(
    "GITHUB_TEAM_SLUG", "github-management-team"
)
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")

# Date Override for testing
TODAY_STR = os.environ.get("TODAY_OVERRIDE")
TODAY = (
    datetime.strptime(TODAY_STR, "%Y-%m-%d").date()
    if TODAY_STR
    else datetime.now().date()
)


def send_gmail_notification(username, days_remaining, expiry_date):
    """Sends direct email warning via Gmail SMTP."""
    subject = f"[Access Expiry Warning] Please remove this intern in bitbucket: {username}"
    body = f"""
Hello Admin,

This is an automated notification from the GitHub Access Management System.

Intern Username: {username}
Remaining Days: {days_remaining} day(s)
Expiry Date: {expiry_date}

Action Required: Please review access permissions for this user.

Note: Automated removal will execute on the expiry date.
"""

    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = ADMIN_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, ADMIN_EMAIL, msg.as_string())
        server.quit()
        print(f"✅ Gmail notification sent for user: {username}")
    except Exception as e:
        print(f"❌ Failed to send Gmail notification: {e}")


def remove_github_team_member(username):
    """Removes user from the dedicated GitHub team."""
    url = f"https://api.github.com/orgs/{GITHUB_ORG}/teams/{GITHUB_TEAM_SLUG}/memberships/{username}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        print(
            f"✅ Successfully removed {username} from team {GITHUB_TEAM_SLUG}"
        )
    else:
        print(
            f"❌ Failed to remove {username}: {response.status_code} - {response.text}"
        )


def process_access_registry():
    """Reads registry and triggers warning or removal."""
    if not os.path.exists("access_registry.json"):
        print("❌ Error: access_registry.json file not found.")
        return

    with open("access_registry.json", "r") as file:
        data = json.load(file)

    for member in data.get("members", []):
        if member.get("access_type") == "temporary":
            username = member["github_username"]
            expires_on = datetime.strptime(
                member["expires_on"], "%Y-%m-%d"
            ).date()
            warning_days = member.get("warning_days", 7)

            days_remaining = (expires_on - TODAY).days

            print(
                f"Checking user: {username} | Days remaining: {days_remaining}"
            )

            # Check for expiry
            if TODAY >= expires_on:
                print(f"User {username} has expired. Removing access...")
                remove_github_team_member(username)

            # Check for warning period
            elif 0 < days_remaining <= warning_days:
                print(
                    f"User {username} is within warning period ({days_remaining} days left). Sending Gmail..."
                )
                send_gmail_notification(
                    username, days_remaining, member["expires_on"]
                )


if __name__ == "__main__":
    process_access_registry()
