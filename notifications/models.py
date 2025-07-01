from django.db import models
from users.models import CustomUser

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('artwork_approved', 'Artwork Approved'),
        ('event_update', 'Event Update'),
        ('project_invite', 'Project Invitation'),
    ]

    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.notification_type} - {self.recipient.email}"
