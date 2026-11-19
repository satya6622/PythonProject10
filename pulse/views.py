import random

from django.contrib.auth import authenticate
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import NotificationLog, PriceAlert
from .permissions import IsAdminUser
from .serializers import PriceAlertSerializer, RegisterSerializer

MOCK_PRICES = {"DEL-BOM": (3000, 7000), "BLR-HYD": (1500, 4000), "DEL-BLR": (4000, 9000), "BOM-GOA": (2000, 5000)}


def access_token_for(user):
    return str(RefreshToken.for_user(user).access_token)


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"username": user.username, "access": access_token_for(user), "role": user.profile.role}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        user = authenticate(username=request.data.get("username", ""), password=request.data.get("password", ""))
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"username": user.username, "access": access_token_for(user), "role": user.profile.role})


class AlertListCreateView(ListCreateAPIView):
    serializer_class = PriceAlertSerializer

    def get_queryset(self):
        return PriceAlert.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AlertDeactivateView(APIView):
    def delete(self, request, pk):
        alert = get_object_or_404(PriceAlert, id=pk)
        if alert.user != request.user:
            return Response(status=status.HTTP_404_NOT_FOUND)
        alert.status = PriceAlert.Status.INACTIVE
        alert.save(update_fields=["status"])
        return Response({"status": PriceAlert.Status.INACTIVE})


class FlightPriceView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        route = request.query_params.get("route", "").upper()
        price_range = MOCK_PRICES.get(route)
        if price_range is None:
            return Response({"error": "Route not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"route": route, "price": random.randint(*price_range)})


class AdminSummaryView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        alert_counts = PriceAlert.objects.aggregate(total_alerts=Count("id"), active_alerts=Count("id", filter=Q(status=PriceAlert.Status.ACTIVE)), triggered_alerts=Count("id", filter=Q(status=PriceAlert.Status.TRIGGERED)))
        top_routes = PriceAlert.objects.values("origin", "destination").annotate(alert_count=Count("id")).order_by("-alert_count", "origin", "destination")[:5]
        return Response({**alert_counts, "total_notifications": NotificationLog.objects.aggregate(total=Count("id"))["total"], "top_routes": [{"route": f"{row['origin']}-{row['destination']}", "alert_count": row["alert_count"]} for row in top_routes]})
