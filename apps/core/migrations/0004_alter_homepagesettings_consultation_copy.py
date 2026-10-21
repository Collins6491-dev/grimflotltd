# Generated for the refined public consultation copy.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0003_homepagesettings_feature_images")]

    operations = [
        migrations.AlterField(
            model_name="homepagesettings",
            name="consultation_copy",
            field=models.TextField(
                default=(
                    "Bring the building, ambition, and constraints to an initial conversation. "
                    "We will help you turn them into a practical next step."
                ),
                max_length=600,
            ),
        ),
    ]
