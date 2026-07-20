import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Ride
from channels.db import database_sync_to_async


class RideTrackingConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get ride_id from URL
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        # Create unique group name for this ride
        self.room_group_name = f'ride_{self.ride_id}'

        if not self.scope['user'].is_authenticated:
            await self.close(code=4001)
            return
        try:
            self.ride = await database_sync_to_async(
                Ride.objects.select_related('passenger', 'driver').get
                           )(id=self.ride_id)
        except Ride.DoesNotExist:
            await self.close(code=4002)
            return
        if self.scope['user'] not in [self.ride.passenger, self.ride.driver]:
            await self.close(code=4003)
            return

        # Join the group — await because it talks to Redis
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept the WebSocket connection
        await self.accept()

    async def disconnect(self, close_code):
        # Remove this connection from the group
        # so no more messages are sent to this closed connection
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        if self.scope['user'] != self.ride.driver:
            await self.send(text_data=json.dumps({
                'error': 'Only the driver can send location updates.'
            }))
            return
        # Step 1 — Parse JSON string into Python dictionary
        try:
            data = json.loads(text_data)

            # Step 2 — Extract values from the dictionary
            latitude = data['latitude']
            longitude = data['longitude']
            speed = data.get('speed')
        except (json.JSONDecodeError, KeyError):
            await self.send(text_data=json.dumps({
                'error': 'Invalid data format'
            }))
            return
        
        # Step 3 — Broadcast to everyone in the group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'location_update',
                'latitude': latitude,
                'longitude': longitude,
                'speed': speed,
            }
        )

    async def location_update(self, event):
        # Send location data to THIS specific connection
        # runs on every consumer in the group
        # so both driver and passenger receive the update
        await self.send(text_data=json.dumps({
            'latitude': event['latitude'],
            'longitude': event['longitude'],
            'speed': event.get('speed'),
        }))


    async def ride_end(self, event):
        # Send ride end event to THIS specific connection
        await self.send(text_data=json.dumps({
            'event': 'ride_end',
            'message': event['message'],
        }))
        await self.close()
    