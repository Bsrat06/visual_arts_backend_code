from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, EventStatsView, UpcomingEventCountView, PastEventViewSet, EventImageViewSet

router = DefaultRouter()
router.register(r'events', EventViewSet)
router.register(r'past-events', PastEventViewSet, basename='past-events')
router.register("event-images", EventImageViewSet, basename="event-image")

urlpatterns = [
    path('', include(router.urls)),
    path('event-stats/', EventStatsView.as_view(), name='event-stats'),
    path('upcoming_count/', UpcomingEventCountView.as_view(), name='upcoming-event-count'),
]
