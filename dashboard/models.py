"""
Dashboard models.

Architecture decision: Minimal Django models — most state lives in BigQuery.

Why: This dashboard is a read-only interface over the gcp-data-pipeline's
BigQuery tables. Storing pipeline run metadata in Django's database would
create a second source of truth that diverges from the actual pipeline state.
Instead, the dashboard reads directly from BigQuery analytics tables and
only stores user preferences (bookmarked queries, filter presets) locally.

The models here are for user-facing features, not pipeline state.
"""

from typing import ClassVar

from django.contrib.auth.models import User
from django.db import models


class BookmarkedQuery(models.Model):
    """
    A saved query filter preset that a user can quickly reapply.

    Architecture decision: Separate model over JSONField on User model.
    Why: JSONField on User would work but makes querying, indexing, and
    migration harder. A separate model with explicit fields is more
    maintainable and allows future features like sharing bookmarks.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="bookmarked_queries"
    )
    name = models.CharField(
        max_length=100, help_text="Human-readable label for this bookmark"
    )
    query_params = models.JSONField(
        default=dict,
        help_text="Filter parameters stored as JSON (date_from, date_to, category, region)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["-created_at"]
        unique_together: ClassVar[list[str]] = ["user", "name"]

    def __str__(self) -> str:
        return f"{self.user.username}: {self.name}"


class DashboardPreference(models.Model):
    """
    Per-user dashboard configuration.

    Architecture decision: Separate model over session-based storage.
    Why: Session storage is ephemeral — preferences reset on logout or
    session expiry. A persistent model means preferences survive across
    sessions, which is the expected UX for a dashboard.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="dashboard_prefs"
    )
    default_date_range_days = models.IntegerField(
        default=30, help_text="Default date range in days"
    )
    default_chart_type = models.CharField(
        max_length=20,
        default="bar",
        choices=[("bar", "Bar"), ("line", "Line"), ("area", "Area")],
    )
    theme = models.CharField(
        max_length=10,
        default="light",
        choices=[("light", "Light"), ("dark", "Dark")],
    )

    def __str__(self) -> str:
        return f"{self.user.username} preferences"
