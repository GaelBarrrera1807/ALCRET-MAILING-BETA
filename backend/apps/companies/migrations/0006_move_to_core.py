# Generated manually — deregister models from companies app state
# via SeparateDatabaseAndState (tables stay, models now live in core app)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0005_alter_company_maps_categories_and_more'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='CompanyContact'),
                migrations.DeleteModel(name='Company'),
                migrations.DeleteModel(name='Product'),
                migrations.DeleteModel(name='Sector'),
            ],
            database_operations=[],
        ),
    ]
