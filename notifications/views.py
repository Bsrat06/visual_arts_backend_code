# notifications/views.py
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Notification
from .serializers import NotificationSerializer
from users.models import CustomUser

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only fetch notifications for the logged-in user
        return self.queryset.filter(recipient=self.request.user)

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def mark_as_read(self, request, pk=None):
        # Mark a notification as read
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response({"message": "Notification marked as read."})
    
    
    @action(detail=False, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def mark_all_as_read(self, request):
        notifications = self.get_queryset()
        notifications.update(read=True)  # Mark all as read for the logged-in user
        return Response({"message": "All notifications marked as read."})
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')



    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdminUser])
    def send_bulk(self, request):
        role = request.data.get("role")
        message = request.data.get("message")
        notification_type = request.data.get("notification_type", "general")
        
        if not role or not message:
            return Response({"error": "Role and message are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        users = CustomUser.objects.filter(role=role)
        notifications = [
            Notification(
                recipient=user,
                message=message,
                notification_type=notification_type
            ) for user in users
        ]
        Notification.objects.bulk_create(notifications)
        return Response({"detail": "Notifications sent successfully"}, status=status.HTTP_200_OK)