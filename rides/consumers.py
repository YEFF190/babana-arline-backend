import json
from channels.generic.websocket import AsyncWebsocketConsumer


class RideTrackingConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get ride_id from URL
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']

        # Create unique group name for this ride
        self.room_group_name = f'ride_{self.ride_id}'

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
        # Step 1 — Parse JSON string into Python dictionary
        data = json.loads(text_data)

        # Step 2 — Extract values from the dictionary
        latitude = data['latitude']
        longitude = data['longitude']
        speed = data.get('speed')

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