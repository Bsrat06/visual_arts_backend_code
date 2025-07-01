from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from users.pagination import CustomPagination
from notifications.models import Notification
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Artwork, Like
from .serializers import ArtworkSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from users.permissions import IsAdminUser
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework import status
from django.db import models
from django.db.models import Count
from rest_framework.permissions import AllowAny

class ArtworkViewSet(viewsets.ModelViewSet):
    queryset = Artwork.objects.all()#.order_by("-submission_date")
    serializer_class = ArtworkSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)  # ✅ Allow file uploads
    pagination_class = CustomPagination  # Use the custom pagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    
    # Enable filtering by approval status and artist
    filterset_fields = ['approval_status', 'artist', 'category']
    
    # Enable search by title or description
    search_fields = ['title', 'description']
    
    # Enable ordering by submission date
    ordering_fields = ['submission_date']


    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            print(f"Permissions checked for admin user: {self.request.user.is_staff}")  # ✅ Debugging log
            permission_classes = [IsAuthenticated, IsAdminUser]
         
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    
    def perform_create(self, serializer):
        serializer.save(artist=self.request.user)


    def perform_update(self, serializer):
        print("Updating Artwork with Data:", serializer.validated_data)  # ✅ Debugging log
        instance = serializer.save()
        
        if instance.approval_status == 'rejected' and 'feedback' in serializer.validated_data:
            Notification.objects.create(
                recipient=instance.artist,
                message=f"Your artwork '{instance.title}' has been rejected. Feedback: {instance.feedback}",
                notification_type='artwork_feedback'
            )
        
        if instance.approval_status == 'approved':
            Notification.objects.create(
                recipient=instance.artist,
                message=f"Your artwork '{instance.title}' has been approved.",
                notification_type='artwork_approved'
            )



    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, IsAdminUser])
    def approve(self, request, pk=None):
        artwork = self.get_object()
        artwork.approval_status = 'approved'
        artwork.save()

        # Send Notification
        Notification.objects.create(
            recipient=artwork.artist,
            message=f"Your artwork '{artwork.title}' has been approved.",
            notification_type='artwork_approved'
        )
        return Response({"message": "Artwork approved successfully."}, status=status.HTTP_200_OK)


    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, IsAdminUser])
    def reject(self, request, pk=None):
        artwork = self.get_object()
        feedback = request.data.get("feedback", "")

        print("Feedback received for rejection:", feedback)  # Debugging log

        if not feedback.strip():
            return Response(
                {"error": "Feedback is required when rejecting an artwork."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        artwork.approval_status = 'rejected'
        artwork.feedback = feedback  # Save the feedback
        artwork.save()

        print("Artwork feedback saved:", artwork.feedback)  # Debugging log

        Notification.objects.create(
            recipient=artwork.artist,
            message=f"Your artwork '{artwork.title}' has been rejected. Feedback: {feedback}",
            notification_type='artwork_rejected'
        )
        return Response({"message": "Artwork rejected successfully."}, status=status.HTTP_200_OK)


    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_artworks(self, request):
        queryset = self.filter_queryset(self.get_queryset().filter(artist=request.user))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    
    
    @action(detail=False, methods=["get"], permission_classes=[IsAdminUser])
    def category_analytics(self, request):
        analytics = (
            Artwork.objects.values("category")
            .annotate(
                total=Count("id"),
                approved=Count("id", filter=models.Q(approval_status="approved")),
                pending=Count("id", filter=models.Q(approval_status="pending")),
                rejected=Count("id", filter=models.Q(approval_status="rejected")),
            )
            .order_by("category")
        )
        return Response(analytics, status=200)
    
    
    

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def like_artwork(request, artwork_id):
    artwork = Artwork.objects.get(id=artwork_id)
    like, created = Like.objects.get_or_create(user=request.user, artwork=artwork)
    if created:
        return Response({"message": "Artwork liked!"}, status=201)
    return Response({"message": "Already liked!"}, status=400)

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def unlike_artwork(request, artwork_id):
    try:
        like = Like.objects.get(user=request.user, artwork_id=artwork_id)
        like.delete()
        return Response({"message": "Like removed!"}, status=200)
    except Like.DoesNotExist:
        return Response({"message": "Like not found"}, status=404)

@api_view(["GET"])
def get_likes_count(request, artwork_id):
    count = Like.objects.filter(artwork_id=artwork_id).count()
    return Response({"likes": count})

class LikedArtworksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # ✅ Get all artwork IDs liked by the user
        liked_artwork_ids = Like.objects.filter(user=user).values_list("artwork_id", flat=True)

        # ✅ Get the actual artwork objects
        liked_artworks = Artwork.objects.filter(id__in=liked_artwork_ids)

        serializer = ArtworkSerializer(liked_artworks, many=True)
        return Response(serializer.data, status=200)
    
    
class FeaturedArtworkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Artwork.objects.filter(approval_status="approved").order_by("-submission_date")[:11]  # Get latest 10 featured artworks
    serializer_class = ArtworkSerializer
    permission_classes = [AllowAny]  # Adjust as needed
    
    
    
class PendingArtworkCountView(APIView):
    def get(self, request):
        count = Artwork.objects.filter(approval_status='pending').count()
        return Response({"count": count})
    
    
    
class ArtworkStatsView(APIView):
    permission_classes = [IsAdminUser]  # Restrict to admin users, adjust as needed

    def get(self, request):
        stats = {
            'pending': Artwork.objects.filter(approval_status='pending').count(),
            'approved': Artwork.objects.filter(approval_status='approved').count(),
            'rejected': Artwork.objects.filter(approval_status='rejected').count(),
            'total': Artwork.objects.count(),
        }
        return Response(stats, status=status.HTTP_200_OK)