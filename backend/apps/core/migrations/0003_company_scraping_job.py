import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_company_companies_c_city_6d9404_idx_and_more'),
        ('scraping', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='company',
                    name='scraping_job',
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='companies', to='scraping.scrapingjob'),
                ),
            ],
            database_operations=[],
        ),
    ]
