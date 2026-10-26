from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("berita", "0007_sheetodon"),
    ]

    operations = [
        migrations.AddField(
            model_name="berita",
            name="relevansi",
            field=models.PositiveSmallIntegerField(
                blank=True, null=True,
                help_text="Nilai Gemini 0-3: seberapa layak berita menjadi fenomena PDRB "
                          "(0 = bukan berita ekonomi, 3 = fenomena kuat)",
            ),
        ),
    ]
