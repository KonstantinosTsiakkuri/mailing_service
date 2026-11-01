from django.urls import path

from users import views

app_name = "users"

urlpatterns = [
    path("", views.UserListView.as_view(), name="user_list"),
    path("<int:pk>/toggle/", views.UserToggleActiveView.as_view(), name="user_toggle_active"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("activate/<uidb64>/<token>/", views.ActivateView.as_view(), name="activate"),
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("password-reset/", views.UserPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", views.UserPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", views.UserPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", views.UserPasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
