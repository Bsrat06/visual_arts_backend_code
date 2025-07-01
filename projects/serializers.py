from rest_framework import serializers
from .models import Project, ProjectProgress
from users.models import CustomUser


class ProjectProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectProgress
        fields = '__all__'
        read_only_fields = ['project']



class ProjectSerializer(serializers.ModelSerializer):
    members = serializers.PrimaryKeyRelatedField(
    queryset=CustomUser.objects.all(), many=True, required=False  # ✅ Allow empty members list
    )
    image = serializers.ImageField(required=False, allow_null=True)
    updates = ProjectProgressSerializer(many=True, read_only=True)  # ✅ Include progress updates
    progress = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['creator']  # ✅ Prevent frontend from passing 'creator'
        extra_kwargs = {
            "title": {"required": True},
            "description": {"required": True},
        }

    def create(self, validated_data):
        progress = validated_data.pop('progress', 0)
        project = super().create(validated_data)
        if progress:
            ProjectProgress.objects.create(project=project, progress=progress, description="Initial progress")
        return project

    def update(self, instance, validated_data):
        progress = validated_data.pop('progress', None)
        instance = super().update(instance, validated_data)
        if progress is not None:
            ProjectProgress.objects.create(project=instance, progress=progress, description="Progress update")
        return instance
    
    

class MemberSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name')  # Adjust based on your CustomUser model

    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'profile_picture']