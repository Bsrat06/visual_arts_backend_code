from rest_framework import serializers
from .models import Event, EventImage
from users.models import CustomUser  # ✅ Import User model
from users.serializers import UserSerializer


class EventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImage
        fields = ["id", "image", "caption"]

class EventSerializer(serializers.ModelSerializer):
    attendees = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), many=True, required=False  # ✅ Handle Many-to-Many attendees correctly
    )
    event_cover = serializers.ImageField(required=False)
    gallery = EventImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['creator']  # ✅ Prevent frontend from passing 'creator'

    def create(self, validated_data):
        request = self.context.get("request")
        creator = request.user if request else None  # ✅ Get logged-in user
        
        # ✅ Ensure 'creator' is removed from validated_data to prevent duplication
        validated_data.pop("creator", None)

        attendees = validated_data.pop("attendees", [])  # ✅ Extract attendees
        event = Event.objects.create(creator=creator, **validated_data)  # ✅ Assign 'creator' separately
        event.attendees.set(attendees)  # ✅ Add attendees separately
        return event




