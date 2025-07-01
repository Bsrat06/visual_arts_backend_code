from django.db import models
from users.models import CustomUser  # ✅ Import your User model

class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    date = models.DateField()
    event_cover = models.ImageField(upload_to="event_covers/", null=True, blank=True)
    attendees = models.ManyToManyField(CustomUser, related_name="events_attending", blank=True)
    creator = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="events_created")  # ✅ Ensure creator is properly defined
    is_completed = models.BooleanField(default=False)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)


    def __str__(self):
        return self.title


class EventRegistration(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="event_registrations")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} registered for {self.event.title}"
    
    
    
class EventImage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to="event_gallery/")
    caption = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Image for {self.event.title}"


