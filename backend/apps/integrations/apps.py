from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.integrations'

    def ready(self):
        import apps.integrations.tasks  # noqa: F401 — force Celery task registration
