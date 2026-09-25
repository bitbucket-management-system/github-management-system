# GitHub Access Management System

Automated member lifecycle management system for GitHub Organizations using GitHub Actions, Python, and Gmail SMTP.

## Architecture & Tech Stack
- **Orchestrator:** GitHub Actions
- **Core Logic:** Python 3.x (`access_control.py`)
- **Data Source:** JSON Registry (`access_registry.json`)
- **Notifications:** Gmail SMTP

## Repository Structure
- `.github/workflows/daily_check.yml`: Daily scheduled workflow execution.
- `access_control.py`: Script evaluating member validity and handling removal/email triggers.
- `access_registry.json`: Registry tracking member access types and expiry dates.
- `requirements.txt`: Python package dependencies.

## Workflow Execution
The system automatically runs daily at 00:00 UTC via GitHub Actions, reading `access_registry.json` to:
1. Trigger a Gmail alert to Admin 7 days prior to expiry.
2. Remove expired temporary members automatically from the organization team.# github-management-system
to get reminder for resign intern
