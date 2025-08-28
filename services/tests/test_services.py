import pytest
from django.contrib.auth import get_user_model
from services.models import ServiceInstance

User = get_user_model()

@pytest.mark.django_db
def test_service_instance_creation():
    user = User.objects.create(email="testuser@gmail.com")
    service = ServiceInstance.objects.create(
        user=user,
        order_id=1,
        service_type="vps",
        configuration={"cpu": "2 vCPU", "ram": "4GB"},
    )
    assert service.status == "pending"
    assert service.service_type == "vps"
