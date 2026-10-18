"""Admin registrations (dev convenience)."""

from django.contrib import admin

from .models import AgentEvent, AgentRun, Offer, ProductGroup, SearchQuery


class OfferInline(admin.TabularInline):
    model = Offer
    extra = 0
    fields = ("site", "title", "price", "mrp", "discount_pct", "rating", "is_sample", "url")
    readonly_fields = fields


class ProductGroupInline(admin.TabularInline):
    model = ProductGroup
    extra = 0
    fields = ("rank", "canonical_name", "best_offer", "match_confidence")
    readonly_fields = fields
    show_change_link = True


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ("user_query", "status", "is_sample", "model_used", "latency_ms", "created_at")
    list_filter = ("status", "is_sample")
    search_fields = ("user_query", "normalized_query", "summary")
    inlines = [ProductGroupInline]
    readonly_fields = ("id", "created_at", "completed_at")


@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    list_display = ("canonical_name", "search", "rank", "best_offer")
    inlines = [OfferInline]


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("title", "site", "price", "mrp", "discount_pct", "is_sample", "source_server")
    list_filter = ("site", "is_sample", "source_server")
    search_fields = ("title",)


class AgentEventInline(admin.TabularInline):
    model = AgentEvent
    extra = 0
    fields = ("seq", "type", "payload", "created_at")
    readonly_fields = fields


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ("search", "status", "model_used", "latency_ms", "tokens_in", "tokens_out", "created_at")
    inlines = [AgentEventInline]
