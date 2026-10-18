"""Persistence models for search runs, product groups and offers."""

import uuid

from django.db import models


class SearchQuery(models.Model):
    """One user search request and its agent run metadata."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_query = models.CharField(max_length=500)
    normalized_query = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    # Request parameters.
    requested_sites = models.JSONField(default=list, blank=True)
    result_limit = models.PositiveSmallIntegerField(default=5)

    # Which MCP servers actually served data for this search.
    source_servers = models.JSONField(default=list, blank=True)
    is_sample = models.BooleanField(default=False, help_text="True when results came from the demo fallback server.")
    error = models.TextField(blank=True)

    # Agent output summary.
    summary = models.TextField(blank=True)
    best_deal_reason = models.TextField(blank=True)
    caveats = models.JSONField(default=list, blank=True)
    model_used = models.CharField(max_length=120, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "search queries"

    def __str__(self) -> str:
        return f"{self.user_query} [{self.status}]"


class ProductGroup(models.Model):
    """A canonical product matched across marketplaces within one search."""

    search = models.ForeignKey(SearchQuery, related_name="groups", on_delete=models.CASCADE)
    rank = models.PositiveSmallIntegerField(default=0)
    canonical_name = models.CharField(max_length=500)
    note = models.TextField(blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    match_confidence = models.FloatField(null=True, blank=True)
    best_offer = models.ForeignKey(
        "Offer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="best_for_groups",
    )

    class Meta:
        ordering = ["rank"]

    def __str__(self) -> str:
        return self.canonical_name


class Offer(models.Model):
    """A single marketplace listing (normalized from any MCP server)."""

    group = models.ForeignKey(ProductGroup, related_name="offers", on_delete=models.CASCADE)
    site = models.CharField(max_length=32, help_text="amazon | flipkart | ...")
    title = models.CharField(max_length=600)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    mrp = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_pct = models.FloatField(null=True, blank=True)
    rating = models.FloatField(null=True, blank=True)
    reviews = models.IntegerField(null=True, blank=True)
    url = models.URLField(max_length=1200)
    image_url = models.URLField(max_length=1200, blank=True)
    seller = models.CharField(max_length=240, blank=True)
    in_stock = models.BooleanField(null=True, blank=True)

    source_server = models.CharField(max_length=80, blank=True)
    is_sample = models.BooleanField(default=False)
    raw = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["price"]

    def __str__(self) -> str:
        return f"{self.site}: {self.title[:60]} @ {self.price}"


class AgentRun(models.Model):
    """Metadata about one execution of the AI agent for a search."""

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    search = models.ForeignKey(SearchQuery, related_name="runs", on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    model_used = models.CharField(max_length=120, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    tokens_in = models.PositiveIntegerField(null=True, blank=True)
    tokens_out = models.PositiveIntegerField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"run for {self.search_id} [{self.status}]"


class AgentEvent(models.Model):
    """Ordered stream events for replay / SSE."""

    run = models.ForeignKey(AgentRun, related_name="events", on_delete=models.CASCADE)
    seq = models.PositiveIntegerField()
    type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["seq"]
        constraints = [
            models.UniqueConstraint(fields=["run", "seq"], name="unique_run_seq"),
        ]

    def __str__(self) -> str:
        return f"#{self.seq} {self.type}"
