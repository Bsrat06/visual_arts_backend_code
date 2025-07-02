from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAdminUser
from .permissions import IsManagerUser
from rest_framework.generics import ListAPIView
from rest_framework import status
from .models import CustomUser, ActivityLog
from .serializers import UserSerializer, ProfileUpdateSerializer, ActivityLogSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Count, Q
from rest_framework.views import APIView
from artwork.models import Artwork
from events.models import Event
from projects.models import Project
from django.utils.timezone import now, timedelta
from django.db.models.functions import TruncMonth
from rest_framework.pagination import PageNumberPagination
from datetime import datetime
from dj_rest_auth.views import PasswordResetView
from django.core.exceptions import ValidationError
import logging



User = get_user_model()


logger = logging.getLogger(__name__)  # Add logging



class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate user using email
        user = authenticate(request, username=email, password=password)

        if not user:
            return Response({"error": "Invalid credentials. Please try again."}, status=status.HTTP_401_UNAUTHORIZED)

        # Check if the user is active
        if not user.is_active:
            return Response({"error": "Your account is pending approval. Please contact an admin."}, status=status.HTTP_403_FORBIDDEN)

        # Generate or retrieve token
        token, created = Token.objects.get_or_create(user=user)

        # Log the login action
        ActivityLog.objects.create(user=user, action='login')

        return Response({
            "token": token.key,
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
        })


class UserPagination(PageNumberPagination):
    page_size = 10


class UserListView(ListAPIView):
    serializer_class = UserSerializer
    pagination_class = UserPagination

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return CustomUser.objects.all()
        elif user.role == 'manager':
            return CustomUser.objects.filter(role='member')  # Managers can only view members
        else:
            return CustomUser.objects.none()  # Members cannot view other users

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # ✅ Enable image uploads

    def get(self, request, pk=None):  # ✅ Accept pk argument
        try:
            if pk:
                user = CustomUser.objects.get(pk=pk)
            else:
                user = request.user  # Default to current user if no pk is provided

            serializer = UserSerializer(user)
            return Response(serializer.data)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)



# users/views.py
class ActivateUserView(APIView):
    permission_classes = [IsAdminUser | IsManagerUser]  # Admins and managers can activate users

    def patch(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
            if user.role in ['admin', 'manager'] and request.user.role != 'admin':
                return Response({"error": "You cannot activate admins or managers"}, status=status.HTTP_403_FORBIDDEN)
            user.is_active = True
            user.save()
            return Response({"message": "User activated successfully."}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class DeactivateUserView(APIView):
    permission_classes = [IsAdminUser | IsManagerUser]  # Admins and managers can deactivate users

    def patch(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
            if user.role in ['admin', 'manager'] and request.user.role != 'admin':
                return Response({"error": "You cannot deactivate admins or managers"}, status=status.HTTP_403_FORBIDDEN)
            user.is_active = False
            user.save()
            return Response({"message": "User deactivated successfully."}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)



class UpdateUserRoleView(APIView):
    permission_classes = [IsAdminUser]  # Only admins can update roles

    def patch(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        role = request.data.get("role")
        if role not in ["admin", "manager", "member"]:  # Updated roles
            return Response({"error": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure only admins can assign the manager role
        if role == "manager" and request.user.role != "admin":
            return Response({"error": "Only admins can assign the manager role"}, status=status.HTTP_403_FORBIDDEN)

        user.role = role
        user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
    

class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # ✅ Allow file uploads

    def put(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "detail": "Profile updated successfully",
                "data": serializer.data,  # ✅ Ensure updated user data is returned
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class ActivityLogListView(ListAPIView):
    queryset = ActivityLog.objects.all().order_by('-timestamp')
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminUser]
    
    
    
class UserPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(request.user.notification_preferences, status=status.HTTP_200_OK)

    def patch(self, request):
        request.user.notification_preferences.update(request.data)
        request.user.save()
        return Response(request.user.notification_preferences, status=status.HTTP_200_OK)





class AnalyticsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Date Filters (Optional)
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if date_from and date_to:
            date_from = datetime.strptime(date_from, "%Y-%m-%d")
            date_to = datetime.strptime(date_to, "%Y-%m-%d")
        else:
            date_from = now() - timedelta(days=30)  # Default: Last 30 days
            date_to = now()

        # User Role Distribution
        user_roles = CustomUser.objects.values('role').annotate(count=Count('role'))

        # Resource Counts
        total_artworks = Artwork.objects.count()
        pending_artworks = Artwork.objects.filter(approval_status='pending').count()
        total_events = Event.objects.count()
        total_projects = Project.objects.count()

        # Recent Activity Logs
        recent_logs = ActivityLog.objects.filter(timestamp__range=[date_from, date_to]).order_by('-timestamp')[:10]

        # Monthly Artwork Submissions (Group by Month)
        monthly_artwork_data = (
            Artwork.objects.filter(submission_date__range=[date_from, date_to])
            .annotate(month=TruncMonth('submission_date'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        return Response({
            "user_roles": user_roles,
            "total_artworks": total_artworks,
            "pending_artworks": pending_artworks,
            "total_events": total_events,
            "total_projects": total_projects,
            "recent_logs": ActivityLogSerializer(recent_logs, many=True).data,
            "monthly_artwork_data": monthly_artwork_data,
        })
        
        
        
class MemberStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Ensure it's a member
        if request.user.role not in ["member", "admin"]:
            return Response({"error": "Access denied"}, status=403)

        # Total Artworks Submitted
        total_artworks = Artwork.objects.filter(artist=request.user).count()

        # Approval Rate
        approved_artworks = Artwork.objects.filter(artist=request.user, approval_status="approved").count()
        approval_rate = (approved_artworks / total_artworks) * 100 if total_artworks > 0 else 0

        
        # Monthly Approval Rate
        current_year = datetime.now().year
        monthly_approval_rate = (
            Artwork.objects.filter(artist=request.user, approval_status="approved", submission_date__year=current_year)
            .annotate(month=TruncMonth("submission_date"))
            .values("month")
            .annotate(approved=Count("id"))
            .order_by("month")
        )
        
        # Category Distribution
        category_stats = Artwork.objects.filter(artist=request.user).values("category").annotate(
            count=Count("category")
        )

        # Recent Activity Logs
        activity_logs = ActivityLog.objects.filter(user=request.user).order_by("-timestamp")[:5]

        return Response({
            "total_artworks": total_artworks,
            "approved_artworks": approved_artworks,
            "approval_rate": round(approval_rate, 2),
            "category_distribution": list(category_stats),
            "recent_activity_logs": [
                {
                    "action": log.action,
                    "resource": log.resource,
                    "timestamp": log.timestamp,
                } for log in activity_logs
            ]
        })
        
        

class CustomPasswordResetView(PasswordResetView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return Response({"message": "If your email exists, a reset link has been sent."})
    


class RegisterView(APIView):
    def post(self, request):
        data = request.data
        data['role'] = 'member'  # Explicitly set the default role to 'member'
        data['is_active'] = False  # Ensure new users are inactive by default

        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Registration successful. Your account is pending approval."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UserStatsView(APIView):
    def get(self, request):
        total_users = CustomUser.objects.count()

        # Calculate % change (e.g., new users in last 30 days vs previous 30 days)
        today = now().date()
        last_month = today - timedelta(days=30)
        prev_month = last_month - timedelta(days=30)

        last_month_count = CustomUser.objects.filter(date_joined__gte=last_month).count()
        prev_month_count = CustomUser.objects.filter(date_joined__gte=prev_month, date_joined__lt=last_month).count()

        change = ((last_month_count - prev_month_count) / prev_month_count * 100) if prev_month_count else 0

        return Response({
            "total": total_users,
            "change": round(change, 2)
        })
        
        

class PendingUserCountView(APIView):
    def get(self, request):
        count = CustomUser.objects.filter(is_active=False).count()
        return Response({"count": count})
