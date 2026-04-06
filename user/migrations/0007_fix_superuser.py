from django.db import migrations


def fix_superuser(apps, schema_editor):
    from django.contrib.auth.models import User
    # Delete and recreate to ensure all flags are set correctly
    User.objects.filter(username="admin").delete()
    User.objects.create_superuser(
        username="admin",
        email="franco02medina@gmail.com",
        password="Admin@2026!"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0006_create_superuser'),
    ]

    operations = [
        migrations.RunPython(fix_superuser, migrations.RunPython.noop),
    ]
