# orders/filters.py
import django_filters
from .models import Order

class OrderFilter(django_filters.FilterSet):
    min_total = django_filters.NumberFilter(field_name="subtotal", lookup_expr="gte")
    max_total = django_filters.NumberFilter(field_name="subtotal", lookup_expr="lte")
    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Order
        fields = ["status", "user"]
