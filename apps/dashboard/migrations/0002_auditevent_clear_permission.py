from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0001_initial")]

    operations = [
        migrations.AlterModelOptions(
            name="auditevent",
            options={
                "ordering": ("-created_at", "-id"),
                "permissions": (("clear_auditevent", "Can clear dashboard activity"),),
            },
        ),
    ]
