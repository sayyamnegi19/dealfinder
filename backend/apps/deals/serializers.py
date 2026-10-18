"""DRF serializers for the deals API."""

from rest_framework import serializers

from .models import Offer, ProductGroup, SearchQuery


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500, trim_whitespace=True)
    sites = serializers.ListField(
        child=serializers.ChoiceField(choices=["amazon", "flipkart"]),
        required=False,
        default=["amazon", "flipkart"],
        min_length=1,
    )
    limit = serializers.IntegerField(min_value=1, max_value=10, required=False, default=5)


class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = [
            "id",
            "site",
            "title",
            "price",
            "mrp",
            "discount_pct",
            "rating",
            "reviews",
            "url",
            "image_url",
            "seller",
            "in_stock",
            "source_server",
            "is_sample",
        ]


class ProductGroupSerializer(serializers.ModelSerializer):
    offers = OfferSerializer(many=True, read_only=True)

    class Meta:
        model = ProductGroup
        fields = [
            "id",
            "rank",
            "canonical_name",
            "note",
            "attributes",
            "match_confidence",
            "best_offer",
            "offers",
        ]


class SearchQueryDetailSerializer(serializers.ModelSerializer):
    groups = ProductGroupSerializer(many=True, read_only=True)

    class Meta:
        model = SearchQuery
        fields = [
            "id",
            "user_query",
            "normalized_query",
            "status",
            "requested_sites",
            "result_limit",
            "source_servers",
            "is_sample",
            "error",
            "summary",
            "best_deal_reason",
            "caveats",
            "model_used",
            "latency_ms",
            "created_at",
            "completed_at",
            "groups",
        ]


class SearchQueryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQuery
        fields = [
            "id",
            "user_query",
            "status",
            "is_sample",
            "summary",
            "created_at",
            "completed_at",
        ]
