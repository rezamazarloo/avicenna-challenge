import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client


class Command(BaseCommand):
    help = "Post samples/notifications.json notifications to the schedule-send API."

    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR) / "samples" / "notifications.json"

        try:
            notifications = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise CommandError(f"Could not read {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"{path} is not valid JSON: {exc}") from exc

        if not isinstance(notifications, list):
            raise CommandError(f"{path} must contain a JSON array.")

        client = Client()

        for index, notification in enumerate(notifications, start=1):
            response = client.post(
                "/api/notifications/schedule-send",
                data=json.dumps(notification),
                content_type="application/json",
            )
            try:
                result = response.json()
            except ValueError:
                result = response.content.decode()

            self.stdout.write(
                f"{index}: status={response.status_code} result={result}"
            )
