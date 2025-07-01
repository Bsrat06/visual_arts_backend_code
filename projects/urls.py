from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, ProjectStatsView, ProjectProgressView, CompleteProjectView, ActiveProjectCountView, BulkDeleteProjectsView, MemberViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'members', MemberViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('project-stats/', ProjectStatsView.as_view(), name='project-stats'),
    path('projects/<int:project_id>/add-update/', ProjectProgressView.as_view(), name="add-update"),
    path('projects/<int:project_id>/complete/', CompleteProjectView.as_view(), name="complete-project"),
    path("projects/active_count/", ActiveProjectCountView.as_view(), name="active-projects-count"),
    path('projects/bulk-delete/', BulkDeleteProjectsView.as_view(), name='bulk-delete-projects'),
]
