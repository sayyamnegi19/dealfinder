"""API routes for the deals app."""

from django.urls import path

from . import views

urlpatterns = [
    path("search/", views.search_create, name="search-create"),
    path("search/<uuid:search_id>/", views.search_detail, name="search-detail"),
    path("search/<uuid:search_id>/stream", views.search_stream, name="search-stream"),
    path("searches/", views.search_list, name="search-list"),
    path("health/mcp/", views.mcp_health, name="mcp-health"),
]
