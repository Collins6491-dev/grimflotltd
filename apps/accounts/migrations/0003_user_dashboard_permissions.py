from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_customerprofile_wishlistitem")]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={
                "ordering": ("-date_joined",),
                "permissions": (("manage_staff", "Can manage staff accounts"), ("manage_roles", "Can manage roles and permissions")),
            },
        ),
    ]
