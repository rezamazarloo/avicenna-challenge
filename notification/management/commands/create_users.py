from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create alice, bob, and carol users with a shared password."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="changeme123",
            help="Password to set for all created users (default: changeme123)",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        password = options["password"]

        for username in ("alice", "bob", "carol"):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com"},
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
                self.stdout.write(self.style.SUCCESS(f"created {username}"))
            else:
                self.stdout.write(f"{username} already exists")
