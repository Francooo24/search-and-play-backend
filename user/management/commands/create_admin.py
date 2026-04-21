from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Create or reset the Django admin superuser"

    def handle(self, *args, **kwargs):
        User.objects.filter(username="admin").delete()
        User.objects.create_superuser(
            username="admin",
            email="franco02medina@gmail.com",
            password="Admin@2026!",
        )
        self.stdout.write(self.style.SUCCESS("Superuser 'admin' created successfully."))
