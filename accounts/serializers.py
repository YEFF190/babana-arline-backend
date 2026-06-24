from rest_framework import serializers
from .models import User

class RequestOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    role = serializers.ChoiceField(choices=['passenger', 'driver'])

    def validate_phone_number(self, value):
        # Make sure the number starts with Cameroon's country code
        if not value.startswith('+237'):
            raise serializers.ValidationError(
                "Phone number must start with +237 (Cameroon code)"
            )
        if len(value) != 13:  # +237 + 9 digits
            raise serializers.ValidationError(
                "Invalid Cameroonian phone number length"
            )
        return value


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=6, min_length=4)