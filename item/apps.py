from django.apps import AppConfig


class ItemConfig(AppConfig):
    name = 'item'

    def ready(self):
        from . import signals  # noqa: F401
