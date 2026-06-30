import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client


class Command(BaseCommand):
    help = "Post samples/state_reports.json to the notification API."

    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR) / "samples" / "state_reports.json"

        try:
            payload = path.read_text(encoding="utf-8")
            reports = json.loads(payload)
        except OSError as exc:
            raise CommandError(f"Could not read {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"{path} is not valid JSON: {exc}") from exc

        if not isinstance(reports, list):
            raise CommandError(f"{path} must contain a JSON array.")

        client = Client()
        for index, report in enumerate(reports, start=1):
            response = client.post(
                "/api/notifications/",
                data=json.dumps(report),
                content_type="application/json",
            )
            self.stdout.write(
                f"{index}: status={response.status_code} "
                f"body={response.content.decode()}"
            )
