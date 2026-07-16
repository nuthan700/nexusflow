import secrets

from django.conf import settings
from django.db import models
from django.utils.text import slugify


def gen_invite_code():
    return secrets.token_urlsafe(6)


class Workspace(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    invite_code = models.CharField(max_length=16, unique=True, default=gen_invite_code)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workspaces_created")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:80]
            slug = base
            i = 1
            while Workspace.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Membership(models.Model):
    ADMIN = "admin"
    MEMBER = "member"
    ROLE_CHOICES = [(ADMIN, "Admin"), (MEMBER, "Member")]

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("workspace", "user")

    def __str__(self):
        return f"{self.user} @ {self.workspace} ({self.role})"


class Channel(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="channels")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, blank=True)
    is_private = models.BooleanField(default=False)
    is_dm = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="channels_created")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("workspace", "slug")
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:80]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.name}" if not self.is_dm else self.name

    def is_member(self, user):
        """Anyone in the workspace can see public channels; private
        channels and DMs require an explicit ChannelMembership row."""
        if not self.is_private and not self.is_dm:
            return Membership.objects.filter(workspace=self.workspace, user=user).exists()
        return ChannelMembership.objects.filter(channel=self, user=user).exists()


class ChannelMembership(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="channel_memberships")

    class Meta:
        unique_together = ("channel", "user")


class Message(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages")
    content = models.TextField(max_length=4000)
    reactions = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user}: {self.content[:30]}"

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.username,
            "content": self.content,
            "reactions": self.reactions,
            "created_at": self.created_at.strftime("%b %d, %I:%M %p"),
        }
