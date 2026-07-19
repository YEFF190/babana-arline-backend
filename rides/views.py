from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .utils import haversine_distance
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from accounts.models import DriverStatus
from .models import Ride, LocationPing
from .serializers import (
    RideRequestSerializer,
    RideStatusSerializer,
    LocationPingSerializer,
    RideDetailSerializer
)
VALID_TRANSITIONS = {
    'accepted': ['in_progress'],
    'in_progress': ['completed'],
}


class RequestRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Only passengers can request rides
        
        if request.user.role ==  'driver':
            active_ride = Ride.objects.filter(
            driver=request.user,
            status__in=['accepted', 'in_progress']
            ).exists()
            if active_ride:
                return Response(
                    {"error": "You already have an active ride, complete it first!!"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        elif request.user.role != 'passenger':
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
        nearby_rides = []
        driver_satus = request.user.driverstatus
        if driver_satus.current_latitude is None or driver_satus.current_longitude is None:
            return Response(
                {"error": "Driver's current location is not set"},
                status=status.HTTP_400_BAD_REQUEST
            )
        for ride in Ride.objects.filter(status='requested'):
            distance = haversine_distance(
                driver_satus.current_latitude,
                driver_satus.current_longitude,
                ride.pickup_latitude,
                ride.pickup_longitude
            )
            if distance <= 3:  # 3 km radius
                ride.distance_km = round(distance, 2)
                nearby_rides.append(ride)

        if nearby_rides:
            serializer = RideDetailSerializer(nearby_rides, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "No nearby rides available"},
                status=status.HTTP_200_OK
            )
            

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
        #Disallow accepting a new ride if the driver has an active one
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

        # Find the ride AND verify the requesting user is the driver
        # If someone else tries to update this ride's status
        # they get a 404 — we don't even tell them the ride exists
        # This is a security pattern called "security through obscurity"
        try:
            ride = Ride.objects.get(id=ride_id, driver=request.user)
        except Ride.DoesNotExist:
            return Response(
                {"error": "Ride not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate incoming data using our serializer
        # partial=True means not all fields are required
        # only the fields sent in the request will be validated
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

        # Consult the rulebook — is this transition allowed?
        # .get(ride.status, []) safely returns empty list
        # if current status has no valid transitions (e.g. completed)
        # meaning no further updates are possible
        if new_status not in VALID_TRANSITIONS.get(ride.status, []):
            return Response(
                {"error": f"Cannot transition from '{ride.status}' to '{new_status}'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Record timestamps for important status changes
        # timezone.now() gives current time in UTC
        # We store UTC and let Flutter convert to local time
        # This avoids timezone confusion across different regions
        if new_status == 'in_progress':
            ride.started_at = timezone.now()
        elif new_status == 'completed':
            ride.completed_at = timezone.now()
            # Notify all connected clients about the ride completion
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'ride_{ride.id}',
                {
                    'type': 'ride_end',
                    'message': 'Ride has been completed.'
                }
            )
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
    
class NearbyDriverView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only passengers can access this
        if request.user.role != 'passenger':
            return Response(
                {"error": "Only passengers can access this"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            passenger_lat = float(request.query_params.get('latitude'))
            passenger_lon = float(request.query_params.get('longitude'))
        except (TypeError, ValueError):
            return Response(
                {"error": "Valid latitude and longitude query parameters are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        nearby_drivers = []
        for driver_record in DriverStatus.objects.filter(is_available=True):
            if driver_record.current_latitude is not None and driver_record.current_longitude is not None:
                distance = haversine_distance(
                    passenger_lat,
                    passenger_lon,
                    driver_record.current_latitude,
                    driver_record.current_longitude
                )
                if distance <= 3:  # 3 km radius
                    nearby_drivers.append({
                        "driver_id": driver_record.driver.id,
                        "full_name": driver_record.driver.full_name,
                        "phone_number": driver_record.driver.phone_number,
                        "current_latitude": driver_record.current_latitude,
                        "current_longitude": driver_record.current_longitude,
                        "distance_km": round(distance, 2)
                    })
        nearby_drivers.sort(key=lambda d: d['distance_km'])
        return Response(nearby_drivers, status=status.HTTP_200_OK)
