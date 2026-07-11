from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Ride, LocationPing
from .serializers import (
    RideRequestSerializer,
    RideStatusSerializer,
    LocationPingSerializer,
    RideDetailSerializer
)


class RequestRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Only passengers can request rides
        if request.user.role != 'passenger':
            return Response(
                {"error": "Only passengers can request rides"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RideRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the ride and assign the logged-in user as passenger
        ride = serializer.save(passenger=request.user)

        return Response(
            RideDetailSerializer(ride).data,
            status=status.HTTP_201_CREATED
        )

class PassengerRideView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only passengers can access this
        if request.user.role != 'passenger':
            return Response(
                {"error": "Only passengers can access this"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get only THIS passenger's rides
        rides = Ride.objects.filter(
            passenger=request.user
        ).order_by('-created_at')

        serializer = RideDetailSerializer(rides, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class AvailableRidesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only drivers can see available rides
        if request.user.role != 'driver':
            return Response(
                {"error": "Only drivers can view available rides"},
                status=status.HTTP_403_FORBIDDEN
            )

        rides = Ride.objects.filter(status='requested')
        serializer = RideDetailSerializer(rides, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcceptRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        # Only drivers can accept rides
        if request.user.role != 'driver':
            return Response(
                {"error": "Only drivers can accept rides"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if driver already has an active ride
        active_ride = Ride.objects.filter(
            driver=request.user,
            status__in=['accepted', 'in_progress']
        ).exists()

        if active_ride:
            return Response(
                {"error": "You already have an active ride, complete it first"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ride = Ride.objects.get(id=ride_id, status='requested')
        except Ride.DoesNotExist:
            return Response(
                {"error": "Ride not found or already taken"},
                status=status.HTTP_404_NOT_FOUND
            )

        ride.driver = request.user
        ride.status = 'accepted'
        ride.save()

        return Response(
            RideDetailSerializer(ride).data,
            status=status.HTTP_200_OK
        )

class UpdateRideStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, ride_id):
        try:
            ride = Ride.objects.get(id=ride_id, driver=request.user)
        except Ride.DoesNotExist:
            return Response(
                {"error": "Ride not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = RideStatusSerializer(
            ride,
            data=request.data,
            partial=True
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        new_status = serializer.validated_data['status']

        # Update timestamps based on status change
        if new_status == 'in_progress':
            ride.started_at = timezone.now()
        elif new_status == 'completed':
            ride.completed_at = timezone.now()

        serializer.save()

        return Response(
            RideDetailSerializer(ride).data,
            status=status.HTTP_200_OK
        )


class SendLocationPingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        # Only drivers send location pings
        if request.user.role != 'driver':
            return Response(
                {"error": "Only drivers can send location pings"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            ride = Ride.objects.get(
                id=ride_id,
                driver=request.user,
                status='in_progress'
            )
        except Ride.DoesNotExist:
            return Response(
                {"error": "Active ride not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = LocationPingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        LocationPing.objects.create(
            ride=ride,
            **serializer.validated_data
        )

        return Response(
            {"message": "Location updated"},
            status=status.HTTP_200_OK
        )



class CancelRideView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, ride_id):

        # Try to find the ride in the database
        # .get() throws DoesNotExist if no ride matches
        # so we always wrap it in try/except to avoid server crash
        try:
            ride = Ride.objects.get(id=ride_id)
        except Ride.DoesNotExist:
            return Response(
                {"error": "Ride not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Ownership check — only the passenger OR driver
        # involved in this specific ride can cancel it
        # request.user comes from the decoded JWT token automatically
        if request.user != ride.passenger and request.user != ride.driver:
            return Response(
                {"error": "You are not part of this ride"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Passenger cancellation rules
        # A passenger can only cancel before the ride starts
        # Once in_progress they are ON the moto — cancellation
        # would be dangerous and unfair to the driver
        if request.user.role == 'passenger':
            if ride.status not in ['requested', 'accepted']:
                return Response(
                    {"error": "Cannot cancel a ride that is already in progress"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Driver cancellation rules
        # A driver can cancel when accepted (before starting)
        # OR when in_progress (emergency: breakdown, accident)
        # This protects the passenger from being stranded at night
        elif request.user.role == 'driver':
            if ride.status not in ['accepted', 'in_progress']:
                return Response(
                    {"error": "You can only cancel a ride you have accepted"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Update status and persist to database
        ride.status = 'cancelled'
        ride.save()

        # Return full ride details so Flutter can update
        # the entire screen without a second API call
        return Response(
            RideDetailSerializer(ride).data,
            status=status.HTTP_200_OK
        )