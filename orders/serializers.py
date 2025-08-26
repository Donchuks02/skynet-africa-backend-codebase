from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusHistory


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.CharField(source='changed_by.email', read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'previous_status', 'new_status', 'reason',
            'changed_by_email', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'changed_by_email']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'service_plan_id', 'quantity', 'price', 'total_price']
        read_only_fields = ['id', 'total_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'user_email',
            'status', 'billing_cycle', 'subtotal',
            'created_at', 'updated_at',
            'items', 'status_history'
        ]
        read_only_fields = [
            'id', 'order_number', 'user', 'user_email',
            'subtotal', 'created_at', 'updated_at',
            'items', 'status_history'
        ]
