from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction, models
from .models import Order, OrderItem, OrderStatusHistory
from .serializers import OrderSerializer, OrderItemSerializer, OrderStatusHistorySerializer
from .filters import OrderFilter
from .permissions import IsOwnerOrAdmin


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing customer orders with its business logic
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter

    def get_queryset(self):
        """Return orders for the authenticated user"""
        qs = Order.objects.select_related('user').prefetch_related('items')
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def get_serializer_context(self):
        """Add request context to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        """Create order for authenticated user"""
        serializer.save(user=self.request.user, status='draft')

    def perform_update(self, serializer):
        """Update order with business logic validation"""
        order = self.get_object()

        if order.status != 'draft' and not self.request.user.is_staff:
            raise PermissionDenied("You can only modify draft orders.")

        old_status = order.status
        instance = serializer.save()

        if old_status != instance.status:
            OrderStatusHistory.objects.create(
                order=instance,
                previous_status=old_status,
                new_status=instance.status,
                changed_by=self.request.user,
                reason=f"Status changed via API by {self.request.user.email}"
            )

    def perform_destroy(self, instance):
        """Only allow deletion of draft orders"""
        order = self.get_object()
        if order.status != 'draft':
            raise PermissionDenied("You can only delete draft orders.")

        OrderStatusHistory.objects.create(
            order=order,
            previous_status=order.status,
            new_status='deleted',
            changed_by=self.request.user,
            reason="Order deleted by user"
        )
        order.delete()

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit order for payment processing"""
        order = self.get_object()

        if order.status != 'draft':
            return Response(
                {'error': 'Order must be in draft status to submit'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not order.items.exists():
            return Response(
                {'error': 'Order must have at least one item'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            order.status = 'pending'
            order.save()

            OrderStatusHistory.objects.create(
                order=order,
                previous_status='draft',
                new_status='pending',
                changed_by=request.user,
                reason='Order submitted for payment'
            )

        return Response({
            'message': 'Order submitted successfully',
            'order_number': order.order_number,
            'total_amount': order.subtotal
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()

        if not order.can_be_cancelled:
            return Response(
                {'error': 'Order cannot be cancelled in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            old_status = order.status
            order.status = 'cancelled'
            order.save()

            reason = request.data.get('reason', 'Cancelled by customer')
            OrderStatusHistory.objects.create(
                order=order,
                previous_status=old_status,
                new_status='cancelled',
                changed_by=request.user,
                reason=reason
            )

        return Response({'message': 'Order cancelled successfully'})

    @action(detail=True, methods=['get'])
    def status_history(self, request, pk=None):
        """Get order status change history"""
        order = self.get_object()
        history = order.status_history.all()
        serializer = OrderStatusHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get order summary statistics for user"""
        queryset = self.get_queryset()

        summary = {
            'total_orders': queryset.count(),
            'draft_orders': queryset.filter(status='draft').count(),
            'pending_orders': queryset.filter(status='pending').count(),
            'completed_orders': queryset.filter(status='completed').count(),
            'cancelled_orders': queryset.filter(status='cancelled').count(),
        }

        if request.user.is_staff:
            summary.update({
                'total_revenue': queryset.filter(status='completed').aggregate(
                    total=models.Sum('subtotal')
                )['total'] or 0,
                'average_order_value': queryset.filter(status='completed').aggregate(
                    avg=models.Avg('subtotal')
                )['avg'] or 0,
            })

        return Response(summary)


class OrderItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing order items with proper validation
    """
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        qs = OrderItem.objects.select_related('order', 'order__user')
        if self.request.user.is_staff:
            return qs
        return qs.filter(order__user=self.request.user)

    def perform_create(self, serializer):
        """Add item to order with validation"""
        order = serializer.validated_data["order"]

        if order.user != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You cannot add items to this order.")

        if order.status != 'draft':
            raise ValidationError("You can only add items to draft orders.")

        serializer.save()

    def perform_update(self, serializer):
        item = self.get_object()
        if item.order.status != 'draft' and not self.request.user.is_staff:
            raise PermissionDenied("You can only modify items in draft orders.")
        serializer.save()

    def perform_destroy(self, instance):
        item = self.get_object()
        if item.order.status != 'draft' and not self.request.user.is_staff:
            raise PermissionDenied("You can only remove items from draft orders.")
        item.delete()

    @action(detail=False, methods=['post'])
    def bulk_add(self, request):
        """Add multiple items to an order at once"""
        order_id = request.data.get('order_id')
        items_data = request.data.get('items', [])

        if not order_id or not items_data:
            return Response(
                {'error': 'order_id and items are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order = get_object_or_404(Order, id=order_id)
        if order.user != request.user and not request.user.is_staff:
            raise PermissionDenied("You cannot add items to this order.")

        if order.status != 'draft':
            return Response(
                {'error': 'Can only add items to draft orders'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_items = []
        with transaction.atomic():
            for item_data in items_data:
                serializer = self.get_serializer(data={**item_data, "order": order.id})
                serializer.is_valid(raise_exception=True)
                created_items.append(serializer.save())

        return Response({
            'message': f'Successfully added {len(created_items)} items',
            'items': OrderItemSerializer(created_items, many=True).data
        })
