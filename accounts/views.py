import random
import string
from django.core.cache import cache
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import RequestOTPSerializer, VerifyOTPSerializer
from .models import User, DriverStatus
from rest_framework_simplejwt.tokens import RefreshToken

def generate_otp():
    """Generate a random 6-digit OTP code."""
    return ''.join(random.choices(string.digits, k=6))

class RequestOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        phone_number = serializer.validated_data['phone_number']
        role = serializer.validated_data['role']

        # Generate OTP and store it temporarily (10 minutes)
        otp = generate_otp()
        cache.set(f"otp_{phone_number}", {
            'otp': otp,
            'role': role
        }, timeout=600)

        # TODO: Replace this with Africa's Talking SMS sending
        # For now we print the OTP in the terminal (development only)
        print(f"OTP for {phone_number}: {otp}")

        return Response(
            {"message": "OTP sent successfully"},
            status=status.HTTP_200_OK
        )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        phone_number = serializer.validated_data['phone_number']
        otp_code = serializer.validated_data['otp_code']

        # Retrieve OTP from cache
        cached_data = cache.get(f"otp_{phone_number}")

        if not cached_data:
            return Response(
                {"error": "OTP expired or never requested"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if cached_data['otp'] != otp_code:
            return Response(
                {"error": "Invalid OTP code"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # OTP is correct — create user if first time, or just log in
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'role': cached_data['role']}
        )
        if created and user.role == 'driver':
            # Create a DriverStatus entry for new drivers
            DriverStatus.objects.create(driver=user)


        # Delete OTP from cache so it can't be reused
        cache.delete(f"otp_{phone_number}")

       # Generate JWT tokens for this user
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return Response({
            "message": "Login successful",
            "user_id": user.id,
            "phone_number": user.phone_number,
            "role": user.role,
            "is_new_user": created,
            "tokens": {
                "access": access_token,
                "refresh": refresh_token,
            }
        }, status=status.HTTP_200_OK)
    


class  UpdateAvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        
        if user.role != 'driver':
            return Response(
                {"error": "Only drivers can update availability"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        is_available = request.data.get('is_available')
        if not isinstance(is_available, bool):
            return Response(
                {"error": "is_available field is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Get or create the DriverStatus for this driver
        driver_status, created = DriverStatus.objects.get_or_create(driver=user)

        # set availability from request 
        driver_status.is_available = request.data.get('is_available')
        driver_status.last_updated = timezone.now()
        driver_status.save()

        return Response({
            "message": "Availability updated successfully",
            "is_available": driver_status.is_available
        }, status=status.HTTP_200_OK)  


class UpdateLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        
        if user.role != 'driver':
            return Response(
                {"error": "Only drivers can update location"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        current_latitude = request.data.get('current_latitude')
        current_longitude = request.data.get('current_longitude')

        if not isinstance(current_latitude, (int, float)) or not isinstance(current_longitude, (int, float)):
            return Response(
                {"error": "Both current_latitude and current_longitude are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create the DriverStatus for this driver
        driver_status, created = DriverStatus.objects.get_or_create(driver=user)

        # Update location and timestamp
        driver_status.current_latitude = current_latitude
        driver_status.current_longitude = current_longitude
        driver_status.last_location_update = timezone.now()
        driver_status.save()

        return Response({
            "message": "Location updated successfully",
            "current_latitude": driver_status.current_latitude,
            "current_longitude": driver_status.current_longitude,
            "last_location_update": driver_status.last_location_update
        }, status=status.HTTP_200_OK)  