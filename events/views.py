from rest_framework import viewsets, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from django.db import models, transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from datetime import datetime
from notifications.models import Notification
from users.permissions import IsAdminUser
from .models import Event, EventRegistration, EventImage
from .serializers import EventSerializer, EventImageSerializer
import logging
from django.utils import timezone


logger = logging.getLogger(__name__)

class EventPagination(PageNumberPagination):
    page_size = 8
    page_size_query_param = 'page_size'
    max_page_size = 100


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('-date')
    serializer_class = EventSerializer
    parser_classes = (MultiPartParser, FormParser)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    pagination_class = EventPagination
    filterset_fields = ['date', 'location']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date']

    def get_permissions(self):
        if self.action in ['create', 'update', 'destroy', 'registrations']:
            permission_classes = [IsAdminUser]
        elif self.action in ['register', 'unregister', 'my_events', 'my_registrations']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        try:
            serializer.save(creator=self.request.user)
            logger.info(f"Event created by {self.request.user.email}")
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            raise

    def perform_update(self, serializer):
        try:
            instance = serializer.save()
            # Notify attendees of changes
            for attendee in instance.attendees.all():
                Notification.objects.create(
                    recipient=attendee,
                    message=f"The event '{instance.title}' has been updated.",
                    notification_type='event_update'
                )
            logger.info(f"Event {instance.id} updated by {self.request.user.email}")
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            raise

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get only upcoming events"""
        queryset = self.filter_queryset(
            self.get_queryset().filter(date__gte=datetime.now())
            )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_events(self, request):
        """Get events created by the current user"""
        user_events = self.filter_queryset(
            self.get_queryset().filter(creator=request.user))
        serializer = self.get_serializer(user_events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def register(self, request, pk=None):
        """Register the authenticated user for an event"""
        event = self.get_object()
        user = request.user

        try:
            with transaction.atomic():
                # Check if registration is allowed
                if event.registration_deadline and datetime.now() > event.registration_deadline:
                    return Response(
                        {"error": "Registration period has ended"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if event.date <= datetime.now().date():
                    return Response(
                        {"error": "Cannot register for past events"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Prevent duplicate registration
                if EventRegistration.objects.filter(user=user, event=event).exists():
                    return Response(
                        {"error": "Already registered for this event"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Check capacity if event has limit
                if event.capacity and event.attendees.count() >= event.capacity:
                    return Response(
                        {"error": "Event has reached maximum capacity"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Create registration record
                registration = EventRegistration.objects.create(
                    user=user,
                    event=event,
                )

                # Add to attendees (optional M2M)
                event.attendees.add(user)

                # Create notification
                Notification.objects.create(
                    recipient=user,
                    message=f"You've successfully registered for {event.title}",
                    notification_type='event_registration'
                )

                logger.info(f"User {user.email} registered for event {event.id}")

                return Response(
                    {
                        "message": "Successfully registered!",
                        "registration_id": registration.id,
                        "event_details": {
                            "title": event.title,
                            "date": event.date,
                            "location": event.location
                        }
                    },
                    status=status.HTTP_201_CREATED
                )

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response(
                {"error": "Registration failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def registered(self, request):
        user = request.user
        registered_events = self.queryset.filter(attendees=user)
        serializer = self.get_serializer(registered_events, many=True)
        return Response(serializer.data)


    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unregister(self, request, pk=None):
        """Unregister from an event"""
        event = self.get_object()
        user = request.user

        try:
            with transaction.atomic():
                registration = get_object_or_404(
                    EventRegistration,
                    user=user,
                    event=event
                )

                # Check if unregistration is allowed
                if event.date <= datetime.now().date():
                    return Response(
                        {"error": "Cannot unregister from past events"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                registration.delete()

                # Remove from attendees if using M2M
                event.attendees.remove(user)

                Notification.objects.create(
                    recipient=user,
                    message=f"You've unregistered from {event.title}",
                    notification_type='event_unregistration'
                )

                logger.info(f"User {user.email} unregistered from event {event.id}")

                return Response(
                    {"message": "Successfully unregistered"},
                    status=status.HTTP_200_OK
                )
                

        except EventRegistration.DoesNotExist:
            return Response(
                {"error": "Not registered for this event"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unregistration error: {str(e)}")
            return Response(
                {"error": "Unregistration failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser])
    def registrations(self, request, pk=None):
        """Get all registrations for an event (admin only)"""
        event = self.get_object()
        registrations = EventRegistration.objects.filter(
            event=event
        ).select_related('user').order_by('-registration_date')

        data = [{
            'user_id': reg.user.id,
            'username': reg.user.username,
            'email': reg.user.email,
            'registration_date': reg.registration_date,
            'attended': reg.attended
        } for reg in registrations]

        return Response(data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_registrations(self, request):
        """Get all events the current user is registered for"""
        registrations = EventRegistration.objects.filter(
            user=request.user
        ).select_related('event').order_by('-registered_at')

        serializer = self.get_serializer(
            [reg.event for reg in registrations],
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def mark_attended(self, request, pk=None):
        """Mark a user as attended (admin only)"""
        event = self.get_object()
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            registration = EventRegistration.objects.get(
                event=event,
                user__id=user_id
            )
            registration.attended = True
            registration.save()

            Notification.objects.create(
                recipient=registration.user,
                message=f"Your attendance for {event.title} has been confirmed",
                notification_type='event_attendance'
            )

            return Response(
                {"message": f"Attendance marked for user {user_id}"},
                status=status.HTTP_200_OK
            )

        except EventRegistration.DoesNotExist:
            return Response(
                {"error": "Registration not found"},
                status=status.HTTP_404_NOT_FOUND
            )
            
            
    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def past(self, request):
        past_events = Event.objects.filter(date__lt=timezone.now()).order_by("-date")
        page = self.paginate_queryset(past_events)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(past_events, many=True)
        return Response(serializer.data)


class EventStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get event statistics"""
        total_events = Event.objects.count()
        completed_events = Event.objects.filter(
            date__lt=datetime.now().date()
        ).count()
        upcoming_events = Event.objects.filter(
            date__gte=datetime.now().date()
        ).count()

        # Participation statistics
        participation_stats = (
            EventRegistration.objects
            .values("event__title", "event__date")
            .annotate(
                participant_count=Count("user"),
                attended_count=Count("user", filter=models.Q(attended=True))
            )
            .order_by("-event__date")
        )

        # User-specific stats if not admin
        user_stats = {}
        if not request.user.is_staff:
            user_registrations = EventRegistration.objects.filter(
                user=request.user
            ).count()
            user_attended = EventRegistration.objects.filter(
                user=request.user,
                attended=True
            ).count()
            user_stats = {
                "registered_events": user_registrations,
                "attended_events": user_attended
            }

        return Response({
            "total_events": total_events,
            "completed_events": completed_events,
            "upcoming_events": upcoming_events,
            "participation_stats": list(participation_stats),
            "user_stats": user_stats
        })
        
        
class UpcomingEventCountView(APIView):
    # permission_classes = [IsAdminUser]

    def get(self, request):
        count = Event.objects.filter(date__gte=datetime.now().date()).count()
        return Response({"count": count}, status=status.HTTP_200_OK)
    
    
class PastEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Event.objects.filter(date__lt=timezone.now()).order_by("-date")
    serializer_class = EventSerializer
    permission_classes = [AllowAny]
    
    
    
class EventImageViewSet(viewsets.ModelViewSet):
    queryset = EventImage.objects.all().order_by("-id")
    serializer_class = EventImageSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event"]

    def perform_create(self, serializer):
        serializer.save()