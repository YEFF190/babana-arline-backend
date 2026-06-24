import random
import string
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import RequestOTPSerializer, VerifyOTPSerializer
from .models import User

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

        # Delete OTP from cache so it can't be reused
        cache.delete(f"otp_{phone_number}")

        return Response({
            "message": "Login successful",
            "user_id": user.id,
            "phone_number": user.phone_number,
            "role": user.role,
            "is_new_user": created
        }, status=status.HTTP_200_OK)