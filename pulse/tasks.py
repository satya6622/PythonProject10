from decimal import Decimal

import requests
from celery import shared_task
from django.conf import settings

from .models import NotificationLog, PriceAlert


@shared_task
def check_prices():
    active_alerts = PriceAlert.objects.filter(status=PriceAlert.Status.ACTIVE)
    for origin, destination in active_alerts.values_list("origin", "destination").distinct():
        try:
            response = requests.get(settings.PRICE_FEED_URL, params={"route": f"{origin}-{destination}"}, timeout=10)
            response.raise_for_status()
            current_price = response.json().get("price")
        except (requests.RequestException, ValueError):
            continue
        if current_price is None:
            continue
        for alert in active_alerts.filter(origin=origin, destination=destination):
            if Decimal(str(current_price)) <= alert.threshold_price:
                send_notification.delay(alert.id, current_price)


@shared_task
def send_notification(alert_id, triggered_price):
    alert = PriceAlert.objects.get(id=alert_id)
    NotificationLog.objects.create(
        alert=alert, triggered_price=triggered_price,
        message=(f"Price alert triggered! {alert.origin}-{alert.destination} is now Rs.{triggered_price} "
                 f"- below your threshold of Rs.{alert.threshold_price}"),
    )
    alert.status = PriceAlert.Status.TRIGGERED
    alert.save(update_fields=["status"])
