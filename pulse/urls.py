from django.urls import path

from .views import AdminSummaryView, AlertDeactivateView, AlertListCreateView, FlightPriceView, LoginView, RegisterView

urlpatterns = [
    path("auth/register/", RegisterView.as_view()), path("auth/login/", LoginView.as_view()),
    path("alerts/", AlertListCreateView.as_view()), path("alerts/<int:pk>/", AlertDeactivateView.as_view()),
    path("flights/price/", FlightPriceView.as_view()), path("admin/summary/", AdminSummaryView.as_view()),
]
