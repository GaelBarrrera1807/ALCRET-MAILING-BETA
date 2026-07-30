# Generated manually — register companies models in core app state
# via SeparateDatabaseAndState (tables stay as companies_* via db_table)

import uuid
import django.db.models.deletion
from django.db import migrations, models


def create_state_operations():
    return [
        migrations.CreateModel(
            name='Sector',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True, default='')),
            ],
            options={
                'db_table': 'companies_sector',
                'verbose_name': 'Sector',
                'verbose_name_plural': 'Sectores',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.TextField(blank=True, default='')),
                ('sectors', models.ManyToManyField(blank=True, db_table='companies_product_sectors', related_name='products', to='core.sector')),
            ],
            options={
                'db_table': 'companies_product',
                'verbose_name': 'Producto',
                'verbose_name_plural': 'Productos',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Company',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=500)),
                ('business_name', models.CharField(blank=True, default='', max_length=500, verbose_name='Razón social')),
                ('rfc', models.CharField(blank=True, default='', max_length=50, verbose_name='RFC')),
                ('description', models.TextField(blank=True, default='')),
                ('website', models.URLField(blank=True, default='')),
                ('email', models.EmailField(blank=True, default='', max_length=254)),
                ('phone', models.CharField(blank=True, default='', max_length=100)),
                ('address', models.TextField(blank=True, default='')),
                ('city', models.CharField(blank=True, default='', max_length=255)),
                ('state', models.CharField(blank=True, default='', max_length=255)),
                ('country', models.CharField(default='México', max_length=255)),
                ('postal_code', models.CharField(blank=True, default='', max_length=20)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('detected_sector', models.CharField(blank=True, default='', max_length=255)),
                ('score', models.IntegerField(default=0)),
                ('is_client', models.BooleanField(default=False)),
                ('is_lead', models.BooleanField(default=True)),
                ('status', models.CharField(choices=[('pending', 'Pendiente'), ('analyzing', 'Analizando'), ('analyzed', 'Analizado'), ('error', 'Error')], default='pending', max_length=50)),
                ('notes', models.TextField(blank=True, default='')),
                ('source', models.CharField(blank=True, default='', max_length=255)),
                ('source_file', models.CharField(blank=True, default='', max_length=500)),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='companies', to='users.organization')),
                ('sector', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='companies', to='core.sector')),
                ('google_rating', models.FloatField(blank=True, null=True)),
                ('google_reviews_count', models.IntegerField(blank=True, null=True)),
                ('maps_categories', models.JSONField(blank=True, default=list, null=True)),
                ('opening_hours', models.JSONField(blank=True, default=dict, null=True)),
                ('main_photo_url', models.URLField(blank=True, max_length=500, null=True)),
            ],
            options={
                'db_table': 'companies_company',
                'verbose_name': 'Empresa',
                'verbose_name_plural': 'Empresas',
                'ordering': ['-score', 'name'],
            },
        ),
        migrations.CreateModel(
            name='CompanyContact',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('position', models.CharField(blank=True, default='', max_length=255)),
                ('email', models.EmailField(blank=True, default='', max_length=254)),
                ('phone', models.CharField(blank=True, default='', max_length=50)),
                ('is_primary', models.BooleanField(default=False)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contacts', to='core.company')),
            ],
            options={
                'db_table': 'companies_companycontact',
                'verbose_name': 'Contacto',
                'verbose_name_plural': 'Contactos',
            },
        ),
        migrations.AddIndex(
            model_name='company',
            index=models.Index(fields=['organization', 'status'], name='companies_c_organiz_042678_idx'),
        ),
        migrations.AddIndex(
            model_name='company',
            index=models.Index(fields=['organization', 'score'], name='companies_c_organiz_f48d94_idx'),
        ),
    ]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=create_state_operations(),
            database_operations=[],
        ),
    ]
