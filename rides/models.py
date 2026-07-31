from django.db import models
from accounts.models import EmergencyContact, User

class Ride(models.Model):

    STATUS_CHOICES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    passenger = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='passenger_rides'
    )
    driver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='driver_rides'
    )
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_address = models.CharField(max_length=255, blank=True)
    dropoff_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_address = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='requested'
    )
    estimated_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ride {self.id} — {self.passenger} → {self.status}"


class LocationPing(models.Model):
    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name='pings'
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    speed = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ping for Ride {self.ride.id} at {self.timestamp}"


class SOSAlert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sos_alerts')
    ride = models.ForeignKey(Ride, on_delete=models.SET_NULL, null=True, blank=True, related_name='sos_alerts')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    triggered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SOS Alert by {self.user} at {self.triggered_at}"


class SOSRecord(models.Model):
    sos_alert = models.ForeignKey(SOSAlert, on_delete=models.CASCADE, related_name='records')
    contact = models.ForeignKey(EmergencyContact, on_delete=models.SET_NULL, null=True, blank=True, related_name='sos_records')
    contact_name = models.CharField(max_length=100, blank=True)
    contact_phone_number = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=[('sent', 'Sent'), ('failed', 'Failed')], default='failed')
    message_id = models.CharField(max_length=100, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        when = self.sent_at or "not sent"
        return f"SOS Response by {self.contact_name} at {when}"