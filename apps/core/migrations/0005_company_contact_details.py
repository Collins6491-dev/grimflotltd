from django.db import migrations, models


COMPANY_DETAILS = {
    "name": "GRIMFLOT LTD",
    "tagline": "Building Smart Homes",
    "email": "grimflotltd@gmail.com",
    "phone": "08032272788",
    "secondary_phone": "09025525545",
    "whatsapp_number": "+234 805 855 7947",
    "address": "Near Frankchris Filling Station, Otukutu Junction, Delta State, Nigeria.",
    "business_hours": "Monday–Friday: 8:00 AM–5:30 PM.",
}


def apply_confirmed_company_details(apps, schema_editor):
    CompanyProfile = apps.get_model("core", "CompanyProfile")
    SocialLink = apps.get_model("core", "SocialLink")

    CompanyProfile.objects.update_or_create(site_id=1, defaults=COMPANY_DETAILS)

    tiktok = SocialLink.objects.filter(label__iexact="TikTok").first()
    if tiktok is None:
        tiktok = SocialLink.objects.filter(url__icontains="tiktok.com").first()
    if tiktok is None:
        SocialLink.objects.create(
            label="TikTok",
            url="https://www.tiktok.com/@grimflot?_r=1&_t=ZS-9AfHeru2Wwh",
            order=0,
            is_published=True,
        )
    else:
        tiktok.label = "TikTok"
        tiktok.url = "https://www.tiktok.com/@grimflot?_r=1&_t=ZS-9AfHeru2Wwh"
        tiktok.is_published = True
        tiktok.save(update_fields=("label", "url", "is_published", "updated_at"))


class Migration(migrations.Migration):
    dependencies = [("core", "0004_alter_homepagesettings_consultation_copy")]

    operations = [
        migrations.AddField(
            model_name="companyprofile",
            name="secondary_phone",
            field=models.CharField(blank=True, default="09025525545", max_length=40),
        ),
        migrations.AlterField(
            model_name="companyprofile",
            name="address",
            field=models.TextField(blank=True, default="Near Frankchris Filling Station, Otukutu Junction, Delta State, Nigeria.", max_length=500),
        ),
        migrations.AlterField(
            model_name="companyprofile",
            name="business_hours",
            field=models.TextField(blank=True, default="Monday–Friday: 8:00 AM–5:30 PM.", max_length=1000),
        ),
        migrations.AlterField(
            model_name="companyprofile",
            name="email",
            field=models.EmailField(blank=True, default="grimflotltd@gmail.com", max_length=254),
        ),
        migrations.AlterField(
            model_name="companyprofile",
            name="phone",
            field=models.CharField(blank=True, default="08032272788", max_length=40),
        ),
        migrations.AlterField(
            model_name="companyprofile",
            name="tagline",
            field=models.CharField(default="Building Smart Homes", max_length=160),
        ),
        migrations.AlterField(
            model_name="companyprofile",
            name="whatsapp_number",
            field=models.CharField(blank=True, default="+234 805 855 7947", max_length=40),
        ),
        migrations.RunPython(apply_confirmed_company_details, migrations.RunPython.noop),
    ]
