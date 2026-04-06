from django.db import migrations


def create_superuser(apps, schema_editor):
    from django.contrib.auth.models import User
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser(
            username="admin",
            email="franco02medina@gmail.com",
            password="Admin@2026!"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0005_passwordreset_alter_pendingverification_options_and_more'),
    ]

    operations = [
        migrations.RunPython(create_superuser, migrations.RunPython.noop),
    ]
