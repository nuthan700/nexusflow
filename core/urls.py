from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .api import ChannelMessagesAPIView

urlpatterns = [
    path("", views.workspace_list, name="workspace_list"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("w/<slug:slug>/", views.workspace_detail, name="workspace_detail"),
    path("w/<slug:slug>/channels/create/", views.channel_create, name="channel_create"),
    path("w/<slug:slug>/c/<slug:channel_slug>/", views.channel_detail, name="channel_detail"),
    path("api/w/<slug:slug>/c/<slug:channel_slug>/messages/", ChannelMessagesAPIView.as_view(), name="api_channel_messages"),
]
