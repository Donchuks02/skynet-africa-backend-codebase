import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from pprint import pprint

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def create_user(db):
    def make_user(**kwargs):
        data = {
            "email": "test@example.com",
            "password": "password123",
            "name": "Test User",
        }
        data.update(kwargs)
        return User.objects.create_user(**data)
    return make_user


def test_register_user(api_client, create_user):
    response = api_client.post("/api/v1/users/register/", {
        "email": "newuser@gmail.com",
        "password": "password123",
        "name": "New User"
    }, format="json")
    assert response.status_code == 201
    # assert "id" in response.data
    assert response.data["email"] == "newuser@gmail.com"



def test_login_user(api_client, create_user):
    user = create_user()
    response = api_client.post("/api/v1/users/login/", {
        "email": user.email,
        "password": "password123"
    }, format="json")
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


def test_logout_user(api_client, create_user):
    user = create_user()
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    response = api_client.post("/api/v1/users/logout/", {"refresh": str(refresh)})
    assert response.status_code == 200
    assert response.data["detail"] == "Successfully logged out."


def test_password_reset_request(api_client, create_user, settings):
    user = create_user(email="reset@example.com")
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    response = api_client.post("/api/v1/users/reset-password/", {"email": user.email})
    # pprint(response.data)
    assert response.status_code == 200
    assert "Password reset link has been sent to your email." in response.data["detail"]


def test_password_reset_confirm(api_client, create_user):
    user = create_user(email="confirm@example.com") 
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.contrib.auth.tokens import PasswordResetTokenGenerator

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)

    response = api_client.post(f"/api/v1/users/reset-password-confirm/{uid}/{token}/",{"new_password": "newpassword123"}, format="json")

    assert response.status_code == 200
    assert response.data["detail"] == "Password reset successful."
