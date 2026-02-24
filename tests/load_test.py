"""
Load test for CloudSync Pro Customer Success FTE API.
Uses Locust: https://locust.io

Install:
    pip install locust

Run (100 users, 10 spawn rate, 2 min):
    locust -f tests/load_test.py --host http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 2m --headless

Or run with web UI:
    locust -f tests/load_test.py --host http://localhost:8000
    # Open http://localhost:8089
"""
import random
import uuid

from locust import HttpUser, between, task


SAMPLE_NAMES = ["Alice Johnson", "Bob Smith", "Carol White", "David Lee", "Emma Davis"]
SAMPLE_EMAILS = [f"test{i}@example.com" for i in range(1, 21)]
SAMPLE_SUBJECTS = [
    "Cannot login to my account",
    "File sync not working",
    "How to add team members",
    "API integration question",
    "Dashboard not loading",
    "Mobile app crash",
    "Notification settings",
    "Export data to CSV",
    "Two-factor authentication setup",
    "Storage limit exceeded",
]
SAMPLE_MESSAGES = [
    "I have been unable to login since yesterday morning. My password reset emails are not arriving.",
    "My files are not syncing between my laptop and phone. The sync icon keeps spinning.",
    "I need to add 5 new team members to my workspace. How do I do this?",
    "I am trying to connect my application to the CloudSync API but getting authentication errors.",
    "The analytics dashboard is showing a blank white screen after I login.",
    "The mobile app crashes immediately when I open the file sync tab.",
    "I want to disable email notifications but the setting does not seem to save.",
    "How can I export all my project data to a CSV file for reporting?",
    "I want to enable two-factor authentication for my account for extra security.",
    "I received a warning that my storage is 95% full. What are my options?",
]
CATEGORIES = ["billing", "technical", "account", "feature_request", "other"]
PRIORITIES = ["low", "medium", "high", "urgent"]

# Store submitted ticket IDs for status checking
_submitted_tickets = []


class SupportAPIUser(HttpUser):
    """Simulates a customer using the support portal."""

    wait_time = between(1, 5)

    @task(5)
    def check_health(self):
        """Lightweight health check — highest frequency."""
        with self.client.get("/health", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Health check failed: {resp.status_code}")

    @task(10)
    def submit_support_form(self):
        """Submit a new support ticket — core workflow."""
        payload = {
            "name":     random.choice(SAMPLE_NAMES),
            "email":    random.choice(SAMPLE_EMAILS),
            "subject":  random.choice(SAMPLE_SUBJECTS),
            "message":  random.choice(SAMPLE_MESSAGES),
            "category": random.choice(CATEGORIES),
            "priority": random.choice(PRIORITIES),
        }
        with self.client.post(
            "/support/submit",
            json=payload,
            catch_response=True,
            name="/support/submit",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                ticket_id = data.get("ticket_id")
                if ticket_id:
                    _submitted_tickets.append(ticket_id)
                    if len(_submitted_tickets) > 500:
                        _submitted_tickets.pop(0)
                resp.success()
            elif resp.status_code == 422:
                resp.failure(f"Validation error: {resp.text[:200]}")
            else:
                resp.failure(f"Submit failed: {resp.status_code}")

    @task(8)
    def check_ticket_status(self):
        """Check status of a previously submitted ticket."""
        if not _submitted_tickets:
            return
        ticket_id = random.choice(_submitted_tickets)
        with self.client.get(
            f"/support/ticket/{ticket_id}",
            catch_response=True,
            name="/support/ticket/[id]",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Status check failed: {resp.status_code}")

    @task(2)
    def check_nonexistent_ticket(self):
        """Simulate user entering wrong ticket ID."""
        fake_id = str(uuid.uuid4())
        with self.client.get(
            f"/support/ticket/{fake_id}",
            catch_response=True,
            name="/support/ticket/[not-found]",
        ) as resp:
            if resp.status_code == 404:
                resp.success()
            else:
                resp.failure(f"Expected 404, got {resp.status_code}")


class AdminAPIUser(HttpUser):
    """Simulates monitoring / ops checks."""

    wait_time = between(10, 30)
    weight = 1  # 1 admin per 10 regular users

    @task
    def monitor_health(self):
        with self.client.get("/health", name="/health [admin]") as resp:
            if resp.status_code != 200:
                resp.failure("Health degraded")
