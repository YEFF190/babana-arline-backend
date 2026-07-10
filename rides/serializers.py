from rest_framework import serializers
from .models import Ride, LocationPing

class RideRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ride
        fields = [
            'id',
            'pickup_latitude',
            'pickup_longitude',
            'pickup_address',
            'dropoff_latitude',
            'dropoff_longitude',
            'dropoff_address',
            'estimated_price',
        ]
        read_only_fields = ['id']


class RideStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ride
        fields = ['id', 'status']
        read_only_fields = ['id']


class LocationPingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPing
        fields = ['latitude', 'longitude', 'speed']


class RideDetailSerializer(serializers.ModelSerializer):
    passenger_phone = serializers.CharField(
        source='passenger.phone_number',
        read_only=True
    )
    driver_phone = serializers.CharField(
        source='driver.phone_number',
        read_only=True
    )

    class Meta:
        model = Ride
        fields = [
            'id',
            'passenger_phone',
            'driver_phone',
            'pickup_latitude',
            'pickup_longitude',
            'pickup_address',
            'dropoff_latitude',
            'dropoff_longitude',
            'dropoff_address',
            'status',
            'estimated_price',
            'created_at',
            'started_at',
            'completed_at',
        ]