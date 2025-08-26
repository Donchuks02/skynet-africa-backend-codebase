import pytest
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem
from orders.serializers import OrderSerializer
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory
from orders.permissions import IsOwnerOrAdmin


User = get_user_model()


@pytest.mark.django_db
class TestOrderModel:
    def test_subtotal_updates_on_item_save(self):
        user = User.objects.create_user(email="alice@example.com", password="pass")
        order = Order.objects.create(user=user)

        item1 = OrderItem.objects.create(order=order, product_name="Book", quantity=2, price=50)
        item2 = OrderItem.objects.create(order=order, product_name="Pen", quantity=3, price=10)

        order.refresh_from_db()
        assert order.subtotal == 130 

    def test_subtotal_updates_on_item_delete(self):
        user = User.objects.create_user(email="bob@example.com", password="pass")
        order = Order.objects.create(user=user)

        item = OrderItem.objects.create(order=order, product_name="Book", quantity=2, price=50)
        order.refresh_from_db()
        assert order.subtotal == 100

        item.delete()
        order.refresh_from_db()
        assert order.subtotal == 0

    def test_status_history_signal(self):
        user = User.objects.create_user(email="carol@example.com", password="pass")
        order = Order.objects.create(user=user, status="pending")

        # Change status
        order.status = "shipped"
        order.save()

        assert order.status_history.count() == 2
        statuses = list(order.status_history.values_list("status", flat=True))
        assert "pending" in statuses
        assert "shipped" in statuses





#  test serializers

User = get_user_model()


@pytest.mark.django_db
class TestOrderSerializer:
    def test_order_serialization(self):
        user = User.objects.create_user(email="dave@example.com", password="pass")
        order = Order.objects.create(user=user, status="pending")
        OrderItem.objects.create(order=order, product_name="Laptop", quantity=1, price=1200)

        serializer = OrderSerializer(order)
        data = serializer.data

        assert data["status"] == "pending"
        assert data["subtotal"] == "1200.00"
        assert len(data["items"]) == 1
        assert data["items"][0]["product_name"] == "Laptop"

    def test_order_deserialization_creates_items(self):
        user = User.objects.create_user(email="eve@example.com", password="pass")
        payload = {
            "status": "pending",
            "items": [
                {"product_name": "Chair", "quantity": 2, "price": "150.00"},
                {"product_name": "Desk", "quantity": 1, "price": "300.00"},
            ]
        }
        serializer = OrderSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        order = serializer.save(user=user)

        assert order.items.count() == 2
        assert float(order.subtotal) == 600.0



# test view

@pytest.mark.django_db
class TestOrderAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="frank@example.com", password="pass")
        self.admin = User.objects.create_superuser(email="admin@example.com", password="admin")

    def test_user_can_create_order_with_items(self):
        self.client.login(email="frank@example.com", password="pass")
        url = reverse("order-list")
        payload = {
            "status": "pending",
            "items": [{"product_name": "Table", "quantity": 1, "price": "200.00"}],
        }
        response = self.client.post(url, payload, format="json")
        assert response.status_code == 201
        assert response.data["subtotal"] == "200.00"

    def test_user_cannot_update_others_order(self):
        other = User.objects.create_user(username="other", password="pass")
        order = Order.objects.create(user=other, status="pending")

        self.client.login(username="frank", password="pass")
        url = reverse("order-detail", args=[order.id])
        response = self.client.patch(url, {"status": "shipped"}, format="json")
        assert response.status_code == 403  # forbidden

    def test_admin_can_update_any_order(self):
        user_order = Order.objects.create(user=self.user, status="pending")
        self.client.login(username="admin", password="admin")
        url = reverse("order-detail", args=[user_order.id])
        response = self.client.patch(url, {"status": "shipped"}, format="json")
        assert response.status_code == 200
        assert response.data["status"] == "shipped"

    def test_filtering_orders_by_status(self):
        self.client.login(username="frank", password="pass")
        Order.objects.create(user=self.user, status="pending")
        Order.objects.create(user=self.user, status="shipped")

        url = reverse("order-list") + "?status=shipped"
        response = self.client.get(url)
        assert response.status_code == 200
        assert all(o["status"] == "shipped" for o in response.data)

    def test_ordering_by_subtotal(self):
        self.client.login(username="frank", password="pass")
        o1 = Order.objects.create(user=self.user, status="pending")
        OrderItem.objects.create(order=o1, product_name="A", quantity=1, price=100)

        o2 = Order.objects.create(user=self.user, status="pending")
        OrderItem.objects.create(order=o2, product_name="B", quantity=1, price=300)

        url = reverse("order-list") + "?ordering=-subtotal"
        response = self.client.get(url)
        subtotals = [float(o["subtotal"]) for o in response.data]
        assert subtotals == sorted(subtotals, reverse=True)



#  test permission


@pytest.mark.django_db
def test_only_owner_or_admin_can_edit():
    factory = APIRequestFactory()
    owner = User.objects.create_user(username="owner", password="pass")
    other = User.objects.create_user(username="other", password="pass")
    admin = User.objects.create_superuser(username="admin", password="admin")

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
