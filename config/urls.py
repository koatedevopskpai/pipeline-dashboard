"""
Root URL configuration.

Architecture decision: Top-level include over direct view imports.
Why: includes keep the root URLconf clean and allow each app to own its URL
patterns. When an app grows, its URLs stay colocated with its views.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("chat/", include("chat.urls")),
]
