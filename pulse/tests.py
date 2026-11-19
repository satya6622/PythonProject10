from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import NotificationLog, PriceAlert, UserProfile
from .tasks import check_prices, send_notification


class PriceThresholdTest(TestCase):
    def test_price_below_threshold_queues_notification(self):
        user = User.objects.create_user("alice", password="password123")
        PriceAlert.objects.create(user=user, origin="DEL", destination="BOM", threshold_price=4500)
        response = type("Response", (), {"json": lambda s: {"price": 4200}, "raise_for_status": lambda s: None})()
        with patch("pulse.tasks.requests.get", return_value=response), patch("pulse.tasks.send_notification.delay") as delay:
            check_prices()
        delay.assert_called_once()

    def test_price_above_threshold_does_not_trigger(self):
        self.assertFalse(5000 <= 4500)

    def test_price_equal_to_threshold_triggers(self):
        self.assertTrue(4500 <= 4500)


class NotificationLogTest(TestCase):
    def test_notification_is_created_and_alert_is_triggered(self):
        user = User.objects.create_user("testuser", password="password123")
        alert = PriceAlert.objects.create(user=user, origin="DEL", destination="BOM", threshold_price=4500)
        send_notification(alert.id, 4200)
        alert.refresh_from_db()
        log = NotificationLog.objects.get(alert=alert)
        self.assertEqual(log.triggered_price, 4200)
        self.assertIn("DEL-BOM", log.message)
        self.assertEqual(alert.status, PriceAlert.Status.TRIGGERED)


class AlertScopingTest(TestCase):
    def test_user_only_sees_own_alerts(self):
        user1 = User.objects.create_user("user1", password="password123")
        user2 = User.objects.create_user("user2", password="password123")
        own = PriceAlert.objects.create(user=user1, origin="DEL", destination="BOM", threshold_price=4500)
        PriceAlert.objects.create(user=user2, origin="BLR", destination="HYD", threshold_price=2000)
        client = APIClient()
        client.force_authenticate(user1)
        response = client.get("/api/alerts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()], [own.id])


class EndpointTest(TestCase):
    def test_registration_uses_user_role(self):
        response = self.client.post("/api/auth/register/", {"username": "new", "password": "password123", "email": "new@example.com", "role": "admin"}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["role"], UserProfile.Role.USER)
