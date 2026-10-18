"""
Dashboard URL patterns.

Architecture decision: Named URL patterns (name=) over reverse_lazy in templates.
Why: Named URLs mean templates reference {% url "dashboard:index" %} instead of
hardcoding "/". Changing a URL pattern in one place updates every template. This
is Django best practice and makes the project maintainable at scale.
"""

from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("daily-summary/", views.daily_summary_view, name="daily_summary"),
    path(
        "category-breakdown/", views.category_breakdown_view, name="category_breakdown"
    ),
    path("pipeline-runs/", views.pipeline_runs_view, name="pipeline_runs"),
    path("data-quality/", views.data_quality_view, name="data_quality"),
]
