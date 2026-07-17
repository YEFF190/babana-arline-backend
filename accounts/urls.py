from django.urls import path
from .views import RequestOTPView, VerifyOTPView, UpdateAvailabilityView, UpdateLocationView

urlpatterns = [
    path('auth/request-otp/', RequestOTPView.as_view(), name='request-otp'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('driver/update-availability/', UpdateAvailabilityView.as_view(), name='update-availability'),
    path('driver/update-location/', UpdateLocationView.as_view(), name='update-location'),
]