from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Workspace, Channel


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "e.g. Nimbus Labs"})}


class JoinWorkspaceForm(forms.Form):
    invite_code = forms.CharField(max_length=16, label="Invite code")


class ChannelForm(forms.ModelForm):
    class Meta:
        model = Channel
        fields = ["name", "is_private"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "e.g. engineering"})}
