from django.db import migrations


def add_player_columns(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE players
              ADD COLUMN IF NOT EXISTS birthdate DATE,
              ADD COLUMN IF NOT EXISTS show_kids BOOLEAN NOT NULL DEFAULT FALSE,
              ADD COLUMN IF NOT EXISTS show_teen BOOLEAN NOT NULL DEFAULT FALSE,
              ADD COLUMN IF NOT EXISTS show_adult BOOLEAN NOT NULL DEFAULT FALSE,
              ADD COLUMN IF NOT EXISTS country VARCHAR(2),
              ADD COLUMN IF NOT EXISTS status VARCHAR(10) NOT NULL DEFAULT 'active'
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_pendingverification_expires_and_more'),
    ]

    operations = [
        migrations.RunPython(add_player_columns, migrations.RunPython.noop),
    ]
