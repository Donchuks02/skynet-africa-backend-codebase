import pytest
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem
from services.models import ServiceInstance
from services.serializers import *
from services.views import *
from rest_framework.test import APIClient
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_service_instance_creation_direct():
    """
    Direct creation of a ServiceInstance (bypassing signals).
    """
    user = User.objects.create(email="testuser@gmail.com")
    service = ServiceInstance.objects.create(
        user=user,
        order_id=1,
        service_type="vps",
        configuration={"cpu": "2 vCPU", "ram": "4GB"},
    )
    assert service.status == "pending"
    assert service.service_type == "vps"


@pytest.mark.django_db
def test_service_instance_created_via_order_signal():
    """
    A ServiceInstance should be created when an Order is marked as 'paid'.
    """
    user = User.objects.create(email="buyer@gmail.com")
    order = Order.objects.create(user=user, status="pending")
    order_item = OrderItem.objects.create(
        order=order,
        item_type="vps",
        configuration={"cpu": "2 vCPU", "ram": "4GB"},
        unit_price=100.00,
        quantity=1
    )

    # Initially no ServiceInstance exists
    assert ServiceInstance.objects.count() == 0

    # Mark the order as completed to trigger the signal
    order.status = "completed"
    order.save()

    service_instance = ServiceInstance.objects.get(order_id=order.id)
    assert service_instance.user == user
    assert service_instance.service_type == "vps"
    assert service_instance.status == "pending"
    assert service_instance.configuration == {"cpu": "2 vCPU", "ram": "4GB"}




# --- Serializer Tests ---

@pytest.mark.django_db
def test_service_instance_serializer():
    """
    Test ServiceInstanceSerializer
    """
    user = User.objects.create(email="seruser@gmail.com")
    instance = ServiceInstance.objects.create(
        user=user,
        order_id="123e4567-e89b-12d3-a456-426614174000",
        service_type="vps",
        configuration={"cpu": "2 vCPU"},
        )
    data = ServiceInstanceSerializer(instance).data
    assert data["service_type"] == "vps"
    assert data["configuration"] == {"cpu": "2 vCPU"}
    assert data["user"] == user.id



@pytest.mark.django_db
def test_service_credentials_serializer():
    """
    Test ServiceCredentialsSerializer
    """
    user = User.objects.create(email="seruser2@gmail.com")
    instance = ServiceInstance.objects.create(
        user=user,
        order_id="123e4567-e89b-12d3-a456-426614174001",
        service_type="vps",
        )
    creds = ServiceCredentials.objects.create(
        service_instance=instance,
        email="creds@example.com",
        password="secret",
        ip_address="127.0.0.1",
        port=2222,
        )
    data = ServiceCredentialsSerializer(creds).data
    assert data["email"] == "creds@example.com"
    assert data["port"] == 2222






# --- ViewSet Tests ---


@pytest.mark.django_db
def test_service_instance_viewset_list():
    """
    Test the list action of the ServiceInstanceViewSet.
    """
    user = User.objects.create(email="apiviewuser@gmail.com")
    ServiceInstance.objects.create(
        user=user,
        order_id="123e4567-e89b-12d3-a456-426614174002",
        service_type="vps",
        )
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("service-instance-list")
    resp = client.get(url)
    assert resp.status_code == 200
    assert len(resp.data) >= 1




@pytest.mark.django_db
def test_service_instance_viewset_restart_action(monkeypatch):
    user = User.objects.create(email="restartuser@gmail.com")
    instance = ServiceInstance.objects.create(
        user=user,
        order_id="123e4567-e89b-12d3-a456-426614174003",
        service_type="vps",
        )
    client = APIClient()
    client.force_authenticate(user=user)
    # Patch the restart_service task
    monkeypatch.setattr("services.views.restart_service.delay", lambda x: None)
    url = reverse("service-instance-restart", args=[instance.id])
    resp = client.post(url)
    assert resp.status_code == 200
    assert resp.data["status"] == "Service restart queued."


@pytest.mark.django_db
def test_service_instance_viewset_reinstall_action(monkeypatch):
    """
    Test the reinstall action of the ServiceInstanceViewSet.
    """
    user = User.objects.create(email="reinstalluser@gmail.com")
    instance = ServiceInstance.objects.create(
        user=user,
        order_id="123e4567-e89b-12d3-a456-426614174004",
        service_type="vps",
        )
    client = APIClient()
    client.force_authenticate(user=user)
    # Patch the reinstall_service task
    monkeypatch.setattr("services.views.reinstall_service.delay", lambda x: None)
    url = reverse("service-instance-reinstall", args=[instance.id])
    resp = client.post(url)
    assert resp.status_code == 200
    assert resp.data["status"] == "Service reinstall queued"
 