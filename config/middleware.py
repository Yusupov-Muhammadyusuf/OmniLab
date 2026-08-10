"""Deployment-wide response controls."""

from django.conf import settings


class SearchIndexControlMiddleware:
    """Keep explicitly marked deployments out of search indexes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.OMNILAB_NOINDEX:
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response
