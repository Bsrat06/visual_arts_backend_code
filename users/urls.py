from django.urls import path, include
from dj_rest_auth.views import PasswordResetView, PasswordResetConfirmView, LogoutView
from .views import CustomAuthToken, UserListView, UserDetailView, DeactivateUserView, ActivateUserView, UpdateUserRoleView, ProfileUpdateView, ActivityLogListView, UserPreferencesView, AnalyticsView, MemberStatsView, CustomPasswordResetView, RegisterView, UserStatsView, PendingUserCountView, CreateSuperuserTempView, UpdateUserRoleCustomColumnTempView

urlpatterns = [
    # Password Reset Endpoints (Manually Defined)
    path('auth/password/reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('auth/password/reset/confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Logout Endpoint
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    # Custom Authentication Paths
    # path('auth/registration/', include('dj_rest_auth.registration.urls')),  # Registration
    path('auth/registration/', RegisterView.as_view(), name='register'),  # Registration
    path('auth/login/', CustomAuthToken.as_view(), name='api_login'),  # Custom login with role
    path("auth/user/", UserDetailView.as_view(), name="user-details"),  # Custom user detail
    path("users/", UserListView.as_view(), name="user-list"),  # Admin user list
    path("users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("users/<int:pk>/deactivate/", DeactivateUserView.as_view(), name="deactivate-user"),
    path("users/<int:pk>/activate/", ActivateUserView.as_view(), name="activate-user"),
    path("users/<int:pk>/update-role/", UpdateUserRoleView.as_view(), name="update-user-role"),
    path("users/preferences/", UserPreferencesView.as_view(), name="update_preferences"),    
    path("auth/profile/update/", ProfileUpdateView.as_view(), name="profile-update"),
    path('activity-logs/', ActivityLogListView.as_view(), name='activity-logs'),
    path("users/member-stats/", MemberStatsView.as_view(), name="member-stats"),
    path("users/stats/", UserStatsView.as_view(), name="user-stats"),
    path("users/pending_count/", PendingUserCountView.as_view(), name="pending-user-count"),

    path('create-temp-admin/', CreateSuperuserTempView.as_view(), name='create_temp_admin'),
path('temp-update-custom-role/', UpdateUserRoleCustomColumnTempView.as_view(), name='temp_update_custom_role'),

]


urlpatterns += [
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
]