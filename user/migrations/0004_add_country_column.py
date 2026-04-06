from django.db import migrations


def add_country_columns(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE players
              ADD COLUMN IF NOT EXISTS country VARCHAR(2)
        """)
        cursor.execute("""
            ALTER TABLE pending_verifications
              ADD COLUMN IF NOT EXISTS country VARCHAR(2)
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_add_player_columns'),
    ]

    operations = [
        migrations.RunPython(add_country_columns, migrations.RunPython.noop),
    ]
