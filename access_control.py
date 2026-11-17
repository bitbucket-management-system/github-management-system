from datetime import datetime, timedelta
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_ORG = os.environ.get("GITHUB_ORG", "bitbucket-management-system")
GITHUB_TEAM_SLUG = os.environ.get(
    "GITHUB_TEAM_SLUG", "github-management-team"
)
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")

DEFAULT_DURATION_DAYS = 180  # 6 months duration

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


def get_github_team_members():
    """Fetches all current members from the GitHub team."""
    url = f"https://api.github.com/orgs/{GITHUB_ORG}/teams/{GITHUB_TEAM_SLUG}/members"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return [member["login"] for member in response.json()]
    else:
        print(
            f"❌ Failed to fetch team members: {response.status_code} - {response.text}"
        )
        return []


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
        return True
    else:
        print(
            f"❌ Failed to remove {username}: {response.status_code} - {response.text}"
        )
        return False


def process_access_registry():
    """Auto-enrolls new team members for 6 months, sends warnings, and removes expired users."""
    if not os.path.exists("access_registry.json"):
        data = {"members": []}
    else:
        with open("access_registry.json", "r") as file:
            data = json.load(file)

    registry_updated = False
    registered_usernames = {
        m["github_username"] for m in data.get("members", [])
    }

    # 1. Auto-detect newly added GitHub team members and grant 6-month (180-day) access
    current_team_members = get_github_team_members()
    for username in current_team_members:
        if username not in registered_usernames:
            expiry_date = (TODAY + timedelta(days=DEFAULT_DURATION_DAYS)).strftime(
                "%Y-%m-%d"
            )
            new_member = {
                "github_username": username,
                "access_type": "temporary",
                "added_on": TODAY.strftime("%Y-%m-%d"),
                "expires_on": expiry_date,
                "warning_days": 7,
            }
            data["members"].append(new_member)
            registered_usernames.add(username)
            registry_updated = True
            print(
                f"🆕 New member detected: {username} | Auto-assigned 6-month access until {expiry_date}"
            )

    # 2. Check existing members for warning or expiry removal
    remaining_members = []
    for member in data.get("members", []):
        if member.get("access_type") != "temporary":
            remaining_members.append(member)
            continue

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
            removed = remove_github_team_member(username)
            if removed:
                registry_updated = True
            else:
                # Keep in registry to retry on next run if API removal failed
                remaining_members.append(member)

        # Check for warning period
        elif 0 < days_remaining <= warning_days:
            print(
                f"User {username} is within warning period ({days_remaining} days left). Sending Gmail..."
            )
            send_gmail_notification(
                username, days_remaining, member["expires_on"]
            )
            remaining_members.append(member)
        else:
            remaining_members.append(member)

    data["members"] = remaining_members

    # Save changes back to access_registry.json if any member was added or removed
    if registry_updated:
        with open("access_registry.json", "w") as file:
            json.dump(data, file, indent=2)
        print("💾 access_registry.json updated successfully.")


if __name__ == "__main__":
    process_access_registry()
