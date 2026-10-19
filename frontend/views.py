from django.views.generic import TemplateView


class AppView(TemplateView):
    """Serves the single-page mobile app shell; all data comes from /api/v1/."""
    template_name = 'frontend/index.html'
