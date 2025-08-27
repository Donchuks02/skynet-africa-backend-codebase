import pytest
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem
from orders.serializers import OrderSerializer
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory
from orders.permissions import IsOwnerOrAdmin


User = get_user_model()



# ----------------------
# Model Tests
# ----------------------

@pytest.mark.django_db
class TestOrderModel:
    # Test that subtotal is correctly updated when items are added to an order
    def test_subtotal_updates_on_item_save(self):
        user = User.objects.create_user(email="alice@example.com", password="pass")
        order = Order.objects.create(user=user)

        OrderItem.objects.create(order=order, service_name="Shared Hosting", quantity=2, unit_price=50)
        OrderItem.objects.create(order=order, service_name="VPS", quantity=3, unit_price=10)

        order.refresh_from_db()
        assert float(order.subtotal) == 130.0

    # Test that subtotal is updated when an item is deleted from an order
    def test_subtotal_updates_on_item_delete(self):
        user = User.objects.create_user(email="bob@example.com", password="pass")
        order = Order.objects.create(user=user)

        item = OrderItem.objects.create(order=order, service_name="GPU VPS", quantity=2, unit_price=50)
        order.refresh_from_db()
        assert float(order.subtotal) == 100.0

        item.delete()
        order.refresh_from_db()
        assert float(order.subtotal) == 0.0

    # Test that status history is recorded when order status changes
    def test_status_history_signal(self):
        from orders.models import OrderStatusHistory
        user = User.objects.create_user(email="carol@example.com", password="pass")
        order = Order.objects.create(user=user, status="pending")

        # Change status to a valid status
        order.status = "confirmed"
        order.save()

        # There should be one status history entry for the change
        assert OrderStatusHistory.objects.filter(order=order).count() == 1
        history = OrderStatusHistory.objects.filter(order=order).first()
        assert history.previous_status == "pending"
        assert history.new_status == "confirmed"




# ----------------------
# Serializer Tests
# ----------------------

@pytest.mark.django_db
class TestOrderSerializer:
    # Test that order serialization returns correct data
    def test_order_serialization(self):
        user = User.objects.create_user(email="dave@example.com", password="pass")
        order = Order.objects.create(user=user, status="pending")
        OrderItem.objects.create(order=order, service_name="Dedicated Cloud", quantity=1, unit_price=1200)

        serializer = OrderSerializer(order)
        data = serializer.data

        assert data["status"] == "pending"
        assert data["subtotal"] == "1200.00"
        assert len(data["items"]) == 1
        assert data["items"][0]["service_name"] == "Dedicated Cloud"

    # Test that deserialization creates order items and calculates subtotal
    def test_order_deserialization_creates_items(self):
        user = User.objects.create_user(email="eve@example.com", password="pass")
        payload = {
            "status": "pending",
            "items": [
                {"service_name": "Domain Registration", "quantity": 2, "unit_price": "150.00"},
                {"service_name": "Professional Email", "quantity": 1, "unit_price": "300.00"},
            ]
        }
        serializer = OrderSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        order = serializer.save(user=user)

        assert order.items.count() == 2
        assert float(order.subtotal) == 600.0


# ----------------------
# API/View Tests
# ----------------------

@pytest.mark.django_db
class TestOrderAPI:
    def setup_method(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        self.client = APIClient()
        self.user = User.objects.create_user(email="frank@example.com", password="pass")
        self.admin = User.objects.create_superuser(email="admin@example.com", password="admin")

        # Get JWT for user
        user_refresh = RefreshToken.for_user(self.user)
        self.user_access_token = str(user_refresh.access_token)

        # Get JWT for admin
        admin_refresh = RefreshToken.for_user(self.admin)
        self.admin_access_token = str(admin_refresh.access_token)

    # Test that a user can create an order with items
    def test_user_can_create_order_with_items(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_access_token)
        url = reverse("order-list")
        payload = {
            "status": "pending",
            "items": [{"service_name": "VPS", "quantity": 1, "unit_price": "200.00"}],
        }
        response = self.client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.data["subtotal"] == "200.00"

    # Test that a user cannot update another user's order
    def test_user_cannot_update_others_order(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_access_token)
        other = User.objects.create_user(email="other@example.com", password="pass")
        order = Order.objects.create(user=other, status="pending")

        url = reverse("order-detail", args=[order.id])
        response = self.client.patch(url, {"status": "confirmed"}, format="json")
        assert response.status_code == 404  # not found (DRF hides existence)

    # Test that an admin can update any order
    def test_admin_can_update_any_order(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.admin_access_token)
        user_order = Order.objects.create(user=self.user, status="pending")
        url = reverse("order-detail", args=[user_order.id])
        response = self.client.patch(url, {"status": "confirmed"}, format="json")
        assert response.status_code == 200
        assert response.data["status"] == "confirmed"

    # Test filtering orders by status
    def test_filtering_orders_by_status(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_access_token)
        Order.objects.create(user=self.user, status="pending")
        Order.objects.create(user=self.user, status="confirmed")

        url = reverse("order-list") + "?status=confirmed"
        response = self.client.get(url)
        assert response.status_code == 200
        assert all(o["status"] == "confirmed" for o in response.data)

    # Test ordering of orders by subtotal in descending order
    def test_ordering_by_subtotal(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user_access_token)
        o1 = Order.objects.create(user=self.user, status="pending")
        OrderItem.objects.create(order=o1, service_name="Shared Hosting", quantity=1, unit_price=100)

        o2 = Order.objects.create(user=self.user, status="pending")
        OrderItem.objects.create(order=o2, service_name="VPS", quantity=1, unit_price=300)

        url = reverse("order-list") + "?ordering=-subtotal"
        response = self.client.get(url)
        subtotals = [float(o["subtotal"]) for o in response.data]
        assert subtotals == sorted(subtotals, reverse=True)




# ----------------------
# Permission Tests
# ----------------------

@pytest.mark.django_db
def test_only_owner_or_admin_can_edit():
    """Test that only the order owner or an admin can edit an order"""
    factory = APIRequestFactory()
    owner = User.objects.create_user(email="owner@example.com", password="pass")
    other = User.objects.create_user(email="other@example.com", password="pass")
    admin = User.objects.create_superuser(email="admin@example.com", password="admin")

    order = Order.objects.create(user=owner)

    # owner can edit
    request = factory.patch("/", {})
    request.user = owner
    assert IsOwnerOrAdmin().has_object_permission(request, None, order) is True

    # other cannot edit
    request.user = other
    assert IsOwnerOrAdmin().has_object_permission(request, None, order) is False

    # admin can edit
    request.user = admin
    assert IsOwnerOrAdmin().has_object_permission(request, None, order) is True
