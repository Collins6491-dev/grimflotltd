import re

from django.db import migrations, models


PREFIXES = {
    "solar": "SOL",
    "solar-panels": "SOL",
    "inverters": "INV",
    "inverter": "INV",
    "cctv": "CCTV",
    "security": "CCTV",
    "security-cameras": "CCTV",
    "smart-locks": "LOCK",
    "access-control": "LOCK",
    "networking": "NET",
    "starlink": "NET",
    "electrical": "ELEC",
}
SKU_PATTERN = re.compile(r"^GRM-([A-Z0-9]+)-(\d+)$")


def backfill_and_seed_sequences(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    SKUSequence = apps.get_model("catalog", "SKUSequence")

    products = list(Product.objects.select_related("category").order_by("id"))
    next_values = {}
    for product in products:
        match = SKU_PATTERN.match((product.sku or "").upper())
        if match:
            prefix, value = match.groups()
            next_values[prefix] = max(next_values.get(prefix, 1), int(value) + 1)

    for product in products:
        if product.sku:
            continue
        prefix = PREFIXES.get(product.category.slug, "GEN")
        value = next_values.get(prefix, 1)
        product.sku = f"GRM-{prefix}-{value:04d}"
        product.save(update_fields=("sku",))
        next_values[prefix] = value + 1

    for prefix, next_value in next_values.items():
        SKUSequence.objects.update_or_create(prefix=prefix, defaults={"next_value": next_value})


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_stockmovement_inventoryrecord_reserved_quantity_and_more")]

    operations = [
        migrations.CreateModel(
            name="SKUSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("prefix", models.CharField(max_length=12, unique=True)),
                ("next_value", models.PositiveIntegerField(default=1)),
            ],
            options={"verbose_name": "SKU sequence", "verbose_name_plural": "SKU sequences"},
        ),
        migrations.RunPython(backfill_and_seed_sequences, migrations.RunPython.noop),
    ]
