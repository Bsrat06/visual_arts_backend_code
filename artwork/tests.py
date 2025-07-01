import pytest
from rest_framework.test import APIClient
from users.models import CustomUser
from artwork.models import Artwork

@pytest.mark.django_db
def test_create_artwork():
    client = APIClient()
    
    # Fix: Set username=None explicitly since our model uses email for authentication
    user = CustomUser.objects.create_user(email="testuser@example.com", password="password123", username=None)
    
    client.force_authenticate(user=user)

    response = client.post("/api/artwork/", {
        "title": "Test Artwork",
        "description": "This is a test artwork.",
        "approval_status": "pending",
        "artist": user.id
    }, format="json")

    assert response.status_code == 201
    assert Artwork.objects.count() == 1
    assert Artwork.objects.first().title == "Test Artwork"
