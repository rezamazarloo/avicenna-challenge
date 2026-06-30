from django.core.management.base import BaseCommand

from notification.state_reports import consume_state_report_batch


class Command(BaseCommand):
    help = "Drain the Redis stream and bulk-update notification state reports."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Drain one batch, then exit.",
        )

    def handle(self, *args, **options):
        while True:
            result = consume_state_report_batch()
            self.stdout.write(str(result))

            if options["once"]:
                return
