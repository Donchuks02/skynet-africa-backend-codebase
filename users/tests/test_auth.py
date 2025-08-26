import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from pprint import pprint

User = get_user_model()

@pytest.fixture
def api_client():
    """
    API client for making HTTP requests.
    """
    return APIClient()

@pytest.fixture
def user_data():
    """
    Centralized user data for tests.
    """
    return {
        "email": "test@example.com",
        "password": "TestPassword123",
        "name": "Test User",
    }

@pytest.fixture
def create_user(db, user_data):
    """
    Factory function for creating users
    """
    def make_user(**kwargs):
        data = user_data.copy()
        data.update(kwargs)
        return User.objects.create_user(**data)
    return make_user



# -------Test users registration-----------

@pytest.mark.django_db
def test_register_user_success(api_client):
    """
    Test successful user registration.
    """
    response = api_client.post("/api/v1/users/register/", {
        "email": "newuser@gmail.com",
        "password": "TestPassword123",
        "name": "New User"
    }, format="json")
    assert response.status_code == 201
    assert response.data["email"] == "newuser@gmail.com"
    assert response.data["name"] == "New User"




@pytest.mark.django_db
def test_register_duplicate_user(api_client, create_user):
    """
    Test registration with an existing email.
    """
    create_user(email="duplicate@example.com")
    response = api_client.post("/api/v1/users/register/", {
        "email": "duplicate@example.com",
        "password": "TestPassword123",
        "name": "Duplicate User"
    }, format="json")
    assert response.status_code == 400
    assert "email" in response.data




@pytest.mark.django_db
def test_register_user_with_invalid_email_format(api_client):
    """
    Test registration with an invalid email format.
    """
    invalid_emails = [
        "invalid-email",
        "invalid@",
        "@invalid.com",
        "invalid.com",
        ""
    ]
    for email in invalid_emails:
        response = api_client.post("/api/v1/users/register/", {
            "email": email,
            "password": "ValidPassword123",
            "name": "Test User"
        }, format="json")
    assert response.status_code == 400
    assert "email" in response.data





# ------- Test users login -----

@pytest.mark.django_db
def test_login_user_success(api_client, create_user, user_data):
    """Test successful user login"""
    create_user()
    
    response = api_client.post("/api/v1/users/login/", {
        "email": user_data["email"],
        "password": user_data["password"]
    }, format="json")
    
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data
    # Ensure tokens are not empty
    assert len(response.data["access"]) > 0
    assert len(response.data["refresh"]) > 0


@pytest.mark.django_db
def test_login_invalid_credentials(api_client, create_user, user_data):
    """Test login with invalid credentials"""
    create_user()
    
    # Wrong password
    response = api_client.post("/api/v1/users/login/", {
        "email": user_data["email"],
        "password": "wrongpassword123"
    }, format="json")
    assert response.status_code == 400
    
    # Wrong email
    response = api_client.post("/api/v1/users/login/", {
        "email": "wrong@example.com",
        "password": user_data["password"]
    }, format="json")
    assert response.status_code == 400
    
    # Both wrong
    response = api_client.post("/api/v1/users/login/", {
        "email": "wrong@example.com",
        "password": "wrongpassword"
    }, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_login_missing_credentials(api_client):
    """Test login with missing credentials"""
    # Missing email
    response = api_client.post("/api/v1/users/login/", {
        "password": "password123"
    }, format="json")
    assert response.status_code == 400
    
    # Missing password
    response = api_client.post("/api/v1/users/login/", {
        "email": "test@example.com"
    }, format="json")
    assert response.status_code == 400
    
    # Both missing
    response = api_client.post("/api/v1/users/login/", {}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_login_nonexistent_user(api_client):
    """Test login with non-existent user"""
    response = api_client.post("/api/v1/users/login/", {
        "email": "nonexistent@example.com",
        "password": "password123"
    }, format="json")
    assert response.status_code == 400




# ---------- Test users logout -------

@pytest.mark.django_db
def test_logout_user_success(api_client, create_user):
    """Test successful user logout"""
    user = create_user()
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    
    response = api_client.post("/api/v1/users/logout/", {
        "refresh": str(refresh)
    })
    
    assert response.status_code == 200
    assert "Successfully logged out" in response.data["detail"]


@pytest.mark.django_db
def test_logout_invalid_token(api_client, create_user):
    """Test logout with invalid refresh token"""
    user = create_user()
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    
    response = api_client.post("/api/v1/users/logout/", {
        "refresh": "invalid_token"
    })
    
    assert response.status_code == 400


@pytest.mark.django_db
def test_logout_missing_token(api_client, create_user):
    """Test logout without refresh token"""
    user = create_user()
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    
    response = api_client.post("/api/v1/users/logout/", {})
    
    assert response.status_code == 400


@pytest.mark.django_db
def test_logout_without_authentication(api_client):
    """Test logout without authentication"""
    response = api_client.post("/api/v1/users/logout/", {
        "refresh": "some_token"
    })
    
    assert response.status_code == 401




# ---------- Test password reset --------------

@pytest.mark.django_db
def test_password_reset_request_success(api_client, create_user, settings):
    """Test successful password reset request"""
    user = create_user(email="reset@example.com")
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    
    response = api_client.post("/api/v1/users/reset-password/", {
        "email": user.email
    })
    
    assert response.status_code == 200
    assert "Password reset link has been sent" in response.data["detail"]

    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to





@pytest.mark.django_db
def test_password_reset_invalid_email(api_client):
    """Test password reset with invalid email format"""
    response = api_client.post("/api/v1/users/reset-password/", {
        "email": "invalid-email"
    })
    
    assert response.status_code == 400


@pytest.mark.django_db
def test_password_reset_missing_email(api_client):
    """Test password reset without email"""
    response = api_client.post("/api/v1/users/reset-password/", {})
    
    assert response.status_code == 400


#------------- Test password reset confirmation --------------

@pytest.mark.django_db
def test_password_reset_confirm_success(api_client, create_user):
    """Test successful password reset confirmation"""
    user = create_user(email="confirm@example.com")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)
    
    response = api_client.post(
        f"/api/v1/users/reset-password-confirm/{uid}/{token}/",
        {"new_password": "NewValidPassword123!"},
        format="json"
    )
    
    assert response.status_code == 200
    assert "Password reset successful" in response.data["detail"]
    
    # Verify user can login with new password
    login_response = api_client.post("/api/v1/users/login/", {
        "email": user.email,
        "password": "NewValidPassword123!"
    }, format="json")
    assert login_response.status_code == 200


@pytest.mark.django_db
def test_password_reset_confirm_invalid_token(api_client, create_user):
    """Test password reset with invalid token"""
    user = create_user(email="confirm@example.com")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    response = api_client.post(
        f"/api/v1/users/reset-password-confirm/{uid}/invalid-token/",
        {"new_password": "NewValidPassword123!"},
        format="json"
    )
    
    assert response.status_code == 400


@pytest.mark.django_db
def test_password_reset_confirm_invalid_uid(api_client, create_user):
    """Test password reset with invalid UID"""
    user = create_user(email="confirm@example.com")
    token = PasswordResetTokenGenerator().make_token(user)
    
    response = api_client.post(
        f"/api/v1/users/reset-password-confirm/invalid-uid/{token}/",
        {"new_password": "NewValidPassword123!"},
        format="json"
    )
    
    assert response.status_code == 400



@pytest.mark.django_db
def test_password_reset_confirm_missing_password(api_client, create_user):
    """Test password reset without new password"""
    user = create_user(email="confirm@example.com")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)
    
    response = api_client.post(
        f"/api/v1/users/reset-password-confirm/{uid}/{token}/",
        {},
        format="json"
    )
    
    assert response.status_code == 400

