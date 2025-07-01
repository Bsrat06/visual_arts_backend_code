from rest_framework import serializers
from .models import Artwork
from users.models import CustomUser

class ArtworkSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True) 
    artist_name = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()  # Add likes count

    
    class Meta:
        model = Artwork
        fields = ['id', 'title', 'description', 'image', 'artist', 'artist_name', 'feedback', 'approval_status', 'submission_date', 'category', "likes_count"]  # ✅ Include 'id' and 'approval_status'
        read_only_fields = ['approval_status', 'feedback', 'artist', 'submission_date']
        
        
    def get_artist_name(self, obj):
        # This method will return the artist's first and last name
        return f"{obj.artist.first_name} {obj.artist.last_name}"    
        
        
    def create(self, validated_data):
        request = self.context.get('request')  # Get the request from the context
        validated_data['artist'] = request.user  # Assign the logged-in user
        return super().create(validated_data)

    def get_likes_count(self, obj):
        return obj.likes.count()  # Return the number of likes