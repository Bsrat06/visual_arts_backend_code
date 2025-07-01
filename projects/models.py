from django.db import models
from users.models import CustomUser
from django.utils import timezone

class Project(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateField(default=timezone.now)  # ✅ Default start date
    end_date = models.DateField(null=True, blank=True)  # ✅ Allow null values
    members = models.ManyToManyField(CustomUser, related_name="projects_participating", blank=True)
    creator = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="projects_created")
    is_completed = models.BooleanField(default=False)
    image = models.ImageField(upload_to="project_images/", null=True, blank=True)


    def __str__(self):
        return self.title


class ProjectProgress(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="updates")
    description = models.TextField()
    image = models.ImageField(upload_to="progress_updates/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Update for {self.project.title} - {self.created_at.strftime('%Y-%m-%d')}"