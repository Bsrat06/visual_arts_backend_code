from notifications.models import Notification
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from users.permissions import IsAdminUser
from .models import Project, ProjectProgress
from .serializers import ProjectSerializer, ProjectProgressSerializer, MemberSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status
from django.utils import timezone
from rest_framework.permissions import AllowAny
from users.models import CustomUser


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    # Enable filtering by start_date and members
    filterset_fields = ['start_date', 'members']

    # Enable search by project title and description
    search_fields = ['title', 'description']

    # Enable ordering by start_date
    ordering_fields = ['start_date']
    
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated]  # Only admins can modify
        else:
            self.permission_classes = [AllowAny]  # Members can only view
        return super().get_permissions()
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
     
    
    
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)  # ✅ Automatically assign logged-in user
        
        
        
    def perform_update(self, serializer):
        instance = serializer.instance
        old_members = set(instance.members.all())
        serializer.save()
        new_members = set(instance.members.all()) - old_members
        for member in new_members:
            Notification.objects.create(
                recipient=member,
                message=f"You have been added to the project '{instance.title}'.",
                notification_type='project_invite'
            )
            
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.creator != request.user and not request.user.is_admin:
            return Response({"error": "You are not authorized to delete this project"}, status=status.HTTP_403_FORBIDDEN)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
            
            
    def get_queryset(self):
        queryset = Project.objects.all()
        if self.request.query_params.get('all') == 'true':
            return queryset  # No pagination
        return queryset
            
            
class ProjectStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total = Project.objects.count()
        in_progress = Project.objects.filter(is_completed=False).count()
        completed = Project.objects.filter(is_completed=True).count()
        recent = Project.objects.filter(start_date__gte=timezone.now() - timezone.timedelta(days=7)).count()
        user_contributions = Project.objects.filter(contributors=request.user).count() if request.user.role == "member" else 0


        # Member-Specific Contributions
        if request.user.role == "member":
            user_contributions = Project.objects.filter(contributors=request.user).count()
        else:
            user_contributions = 0  # Not applicable for admins

        return Response({
            "total": total,
            "in_progress": in_progress,
            "completed": completed,
            "recent": recent,
            "user_contributions": user_contributions,
        })
        
        
        

class ProjectProgressView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, project_id):
        try:
            project = Project.objects.get(id=project_id)
            serializer = ProjectProgressSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(project=project)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

class CompleteProjectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        try:
            project = Project.objects.get(id=project_id)
            if project.creator != request.user:
                return Response({"error": "You are not authorized to complete this project"}, status=status.HTTP_403_FORBIDDEN)

            project.is_completed = True
            project.end_date = timezone.now()
            project.save()
            return Response({"message": "Project marked as completed!"}, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
        
        

class ActiveProjectCountView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        count = Project.objects.filter(is_active=True).count()
        return Response({"count": count})
    
    
class BulkDeleteProjectsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        project_ids = request.data.get('project_ids', [])
        if not project_ids:
            return Response({"error": "No project IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
        projects = Project.objects.filter(id__in=project_ids, creator=request.user)
        count = projects.count()
        projects.delete()
        return Response({"message": f"{count} projects deleted successfully"}, status=status.HTTP_200_OK)
    
    

class MemberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomUser.objects.filter(is_active=True)  # Only active users
    serializer_class = MemberSerializer
    permission_classes = [IsAuthenticated]