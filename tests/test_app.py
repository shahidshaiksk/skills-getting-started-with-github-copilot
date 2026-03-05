"""
Comprehensive test suite for the Mergington High School API (FastAPI application)
Tests cover all endpoints with various scenarios including happy paths and error cases
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Fixture providing a TestClient for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Fixture to reset activities to initial state after each test"""
    # Store original state
    original_activities = {
        key: {
            "description": value["description"],
            "schedule": value["schedule"],
            "max_participants": value["max_participants"],
            "participants": value["participants"].copy()
        }
        for key, value in activities.items()
    }

    yield

    # Restore original state
    for key in list(activities.keys()):
        if key in original_activities:
            activities[key]["participants"] = original_activities[key]["participants"].copy()


class TestActivitiesAPI:
    """Test suite for the activities API endpoints"""

    def test_get_activities_success(self, client):
        """Test GET /activities returns all activities with correct structure"""
        response = client.get("/activities")

        assert response.status_code == 200
        data = response.json()

        # Should return a dictionary of activities
        assert isinstance(data, dict)
        assert len(data) > 0  # Should have activities

        # Check structure of first activity
        first_activity = next(iter(data.values()))
        required_keys = ["description", "schedule", "max_participants", "participants"]
        for key in required_keys:
            assert key in first_activity

        # Participants should be a list
        assert isinstance(first_activity["participants"], list)

    def test_get_activities_contains_expected_activities(self, client):
        """Test that GET /activities returns expected activity names"""
        response = client.get("/activities")
        data = response.json()

        expected_activities = [
            "Chess Club", "Programming Class", "Gym Class", "Basketball Team",
            "Tennis Club", "Debate Team", "Science Club", "Art Class", "Music Ensemble"
        ]

        for activity in expected_activities:
            assert activity in data
            assert "description" in data[activity]
            assert "schedule" in data[activity]
            assert "max_participants" in data[activity]
            assert "participants" in data[activity]

    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        activity_name = "Chess Club"
        email = "test@student.edu"

        response = client.post(f"/activities/{activity_name}/signup?email={email}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert f"Signed up {email} for {activity_name}" in data["message"]

        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]

    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity returns 404"""
        activity_name = "NonExistentActivity"
        email = "test@student.edu"

        response = client.post(f"/activities/{activity_name}/signup?email={email}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]

    def test_signup_duplicate_participant(self, client, reset_activities):
        """Test signing up the same student twice returns error"""
        activity_name = "Chess Club"
        email = "test@student.edu"

        # First signup should succeed
        response1 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response1.status_code == 200

        # Second signup should fail
        response2 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data
        assert "Student already signed up" in data["detail"]

    def test_signup_with_special_characters(self, client, reset_activities):
        """Test signup with activity names containing spaces and special characters"""
        activity_name = "Programming Class"  # Contains space
        email = "test@example.com"

        response = client.post(f"/activities/{activity_name}/signup?email={email}")

        assert response.status_code == 200
        data = response.json()
        assert f"Signed up {email} for {activity_name}" in data["message"]

    def test_unregister_success(self, client, reset_activities):
        """Test successful unregister from an activity"""
        activity_name = "Chess Club"
        email = "test@student.edu"

        # First sign up
        client.post(f"/activities/{activity_name}/signup?email={email}")

        # Then unregister
        response = client.delete(f"/activities/{activity_name}/signup?email={email}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert f"Unregistered {email} from {activity_name}" in data["message"]

        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]

    def test_unregister_activity_not_found(self, client):
        """Test unregister from non-existent activity returns 404"""
        activity_name = "NonExistentActivity"
        email = "test@student.edu"

        response = client.delete(f"/activities/{activity_name}/signup?email={email}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]

    def test_unregister_student_not_signed_up(self, client, reset_activities):
        """Test unregistering a student who is not signed up returns error"""
        activity_name = "Chess Club"
        email = "notsignedup@student.edu"

        response = client.delete(f"/activities/{activity_name}/signup?email={email}")

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Student not signed up" in data["detail"]

    def test_unregister_with_special_characters(self, client, reset_activities):
        """Test unregister with activity names containing spaces"""
        activity_name = "Programming Class"
        email = "test@example.com"

        # Sign up first
        client.post(f"/activities/{activity_name}/signup?email={email}")

        # Then unregister
        response = client.delete(f"/activities/{activity_name}/signup?email={email}")

        assert response.status_code == 200
        data = response.json()
        assert f"Unregistered {email} from {activity_name}" in data["message"]

    def test_multiple_signups_different_activities(self, client, reset_activities):
        """Test signing up for multiple different activities"""
        email = "test@student.edu"
        activities_to_join = ["Chess Club", "Programming Class"]

        for activity_name in activities_to_join:
            response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert response.status_code == 200

        # Verify student is in both activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()

        for activity_name in activities_to_join:
            assert email in activities_data[activity_name]["participants"]

    def test_signup_and_unregister_workflow(self, client, reset_activities):
        """Test complete workflow: signup, verify, unregister, verify"""
        activity_name = "Chess Club"
        email = "workflowtest@student.edu"

        # Initial state - not signed up
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]

        # Sign up
        signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert signup_response.status_code == 200

        # Verify signed up
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]

        # Unregister
        unregister_response = client.delete(f"/activities/{activity_name}/signup?email={email}")
        assert unregister_response.status_code == 200

        # Verify unregistered
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]

    def test_root_redirect(self, client):
        """Test GET / redirects to static index"""
        response = client.get("/")

        assert response.status_code == 200
        # FastAPI redirects are handled, but we can check the response
        # The redirect response should have the correct location
        assert response.url.path == "/static/index.html" or "static/index.html" in str(response.content)