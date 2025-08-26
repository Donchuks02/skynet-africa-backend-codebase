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
    order = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'service_plan_id', 'quantity', 'unit_price', 'total_price', 'service_name']
        read_only_fields = ['id', 'total_price', 'order']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
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
            'status_history'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order
