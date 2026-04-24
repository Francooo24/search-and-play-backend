import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Create or reset the Django admin superuser"

    def handle(self, *args, **kwargs):
        username = os.environ.get("DJANGO_ADMIN_USERNAME", "admin")
        email    = os.environ.get("DJANGO_ADMIN_EMAIL", "")
        password = os.environ.get("DJANGO_ADMIN_PASSWORD", "")

        if not email or not password:
            raise CommandError(
                "DJANGO_ADMIN_EMAIL and DJANGO_ADMIN_PASSWORD environment variables must be set."
            )

        User.objects.filter(username=username).delete()
        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully."))
