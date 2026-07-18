from django.urls import path
from .views import (
    CancelRideView,
    RequestRideView,
    PassengerRideView,
    AvailableRidesView,
    AcceptRideView,
    UpdateRideStatusView,
    SendLocationPingView,
    NearbyDriverView,
)

urlpatterns = [
    # Passenger endpoints
    path('rides/request/', RequestRideView.as_view(), name='request-ride'),
    path('rides/my-rides/', PassengerRideView.as_view(), name='my-rides'),

    # Driver endpoints
    path('rides/available/', AvailableRidesView.as_view(), name='available-rides'),
    path('rides/<int:ride_id>/accept/', AcceptRideView.as_view(), name='accept-ride'),
    path('rides/<int:ride_id>/status/', UpdateRideStatusView.as_view(), name='update-status'),
    path('rides/<int:ride_id>/ping/', SendLocationPingView.as_view(), name='location-ping'),

    # Shared endpoints (passenger and driver)
    path('rides/<int:ride_id>/cancel/', CancelRideView.as_view(), name='cancel-ride'),
    path('rides/nearby-drivers/', NearbyDriverView.as_view(), name='nearby-drivers'),
]