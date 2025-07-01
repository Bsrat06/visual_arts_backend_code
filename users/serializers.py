from rest_framework import serializers
from .models import CustomUser, ActivityLog

class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ["pk", "username", "email", "first_name", "last_name", "is_staff", "is_superuser", "role", "profile_picture", "is_active"]
        extra_kwargs = {
            'role': {'read_only': False},  # Allow role to be set during registration
            "username": {"required": False},
            'is_active': {'read_only': False},  # Allow is_active to be set during registration
        }

    def get_profile_picture(self, obj):
        request = self.context.get("request")
        if obj.profile_picture:
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        return None
        
        
class ProfileUpdateSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()  # ✅ Return full image URL

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "email", "password", "profile_picture", "profile_picture_url"]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
        }

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.profile_picture.url)
        return None  # Return None if no profile picture is set

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        instance = super().update(instance, validated_data)

        # ✅ Log activity
        ActivityLog.objects.create(user=instance, action='update', resource='Profile')

        return instance

    
    
class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'action', 'resource', 'timestamp']
        
        
        
class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["notification_preferences"]

    def update(self, instance, validated_data):
        instance.notification_preferences = validated_data.get("notification_preferences", instance.notification_preferences)
        instance.save()
        return instance
