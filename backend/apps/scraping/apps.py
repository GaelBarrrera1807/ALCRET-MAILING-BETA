from django.apps import AppConfig


class ScrapingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.scraping'

    def ready(self):
        import apps.scraping.tasks  # noqa: F401 — force Celery task registration
