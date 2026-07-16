from rest_framework import generics, serializers
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Channel, Message, Workspace


class MessageSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "user", "content", "reactions", "created_at"]


class ChannelMessagesAPIView(generics.ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        workspace = get_object_or_404(Workspace, slug=self.kwargs["slug"])
        channel = get_object_or_404(Channel, workspace=workspace, slug=self.kwargs["channel_slug"])
        if not channel.is_member(self.request.user):
            raise PermissionDenied("You don't have access to this channel.")
        return channel.messages.select_related("user").order_by("created_at")
