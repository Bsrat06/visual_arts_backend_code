# notifications/serializers.py
from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'message', 'notification_type', 'created_at', 'read']
        read_only_fields = ['recipient', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['recipient'] = request.user  # Assign the logged-in user
        else:
            raise serializers.ValidationError({"recipient": "Recipient must be provided."})
        
        return super().create(validated_data)
