# State-only — tables created by core.0001_initial (db_table='companies_*')
# Keeps the companies migration graph intact for dependency resolution.

import uuid
from django.db import migrations, models


def create_state_operations():
    return [
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
            ],
            options={
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
            ],
            options={
                'verbose_name': 'Contacto',
                'verbose_name_plural': 'Contactos',
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
            ],
            options={
                'verbose_name': 'Producto',
                'verbose_name_plural': 'Productos',
                'ordering': ['name'],
            },
        ),
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
                'verbose_name': 'Sector',
                'verbose_name_plural': 'Sectores',
                'ordering': ['name'],
            },
        ),
    ]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=create_state_operations(),
            database_operations=[],
        ),
    ]
