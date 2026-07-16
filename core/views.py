from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .forms import SignUpForm, WorkspaceForm, JoinWorkspaceForm, ChannelForm
from .models import Workspace, Membership, Channel


def signup(request):
    if request.user.is_authenticated:
        return redirect("workspace_list")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("workspace_list")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def workspace_list(request):
    memberships = Membership.objects.filter(user=request.user).select_related("workspace")

    create_form = WorkspaceForm()
    join_form = JoinWorkspaceForm()

    if request.method == "POST":
        if "create" in request.POST:
            create_form = WorkspaceForm(request.POST)
            if create_form.is_valid():
                workspace = create_form.save(commit=False)
                workspace.created_by = request.user
                workspace.save()
                Membership.objects.create(workspace=workspace, user=request.user, role=Membership.ADMIN)
                Channel.objects.create(workspace=workspace, name="general", created_by=request.user)
                return redirect("workspace_detail", slug=workspace.slug)
        elif "join" in request.POST:
            join_form = JoinWorkspaceForm(request.POST)
            if join_form.is_valid():
                code = join_form.cleaned_data["invite_code"].strip()
                try:
                    workspace = Workspace.objects.get(invite_code=code)
                    Membership.objects.get_or_create(workspace=workspace, user=request.user, defaults={"role": Membership.MEMBER})
                    return redirect("workspace_detail", slug=workspace.slug)
                except Workspace.DoesNotExist:
                    messages.error(request, "No workspace matches that invite code.")

    return render(
        request,
        "core/workspace_list.html",
        {"memberships": memberships, "create_form": create_form, "join_form": join_form},
    )


@login_required
def workspace_detail(request, slug):
    workspace = get_object_or_404(Workspace, slug=slug)
    membership = get_object_or_404(Membership, workspace=workspace, user=request.user)
    channels = [c for c in workspace.channels.filter(is_dm=False) if c.is_member(request.user)]
    if channels:
        return redirect("channel_detail", slug=workspace.slug, channel_slug=channels[0].slug)
    return render(request, "core/workspace_detail.html", {"workspace": workspace, "membership": membership})


@login_required
def channel_create(request, slug):
    workspace = get_object_or_404(Workspace, slug=slug)
    get_object_or_404(Membership, workspace=workspace, user=request.user)
    if request.method == "POST":
        form = ChannelForm(request.POST)
        if form.is_valid():
            channel = form.save(commit=False)
            channel.workspace = workspace
            channel.created_by = request.user
            channel.save()
            return redirect("channel_detail", slug=workspace.slug, channel_slug=channel.slug)
    return redirect("workspace_detail", slug=workspace.slug)


@login_required
def channel_detail(request, slug, channel_slug):
    workspace = get_object_or_404(Workspace, slug=slug)
    membership = get_object_or_404(Membership, workspace=workspace, user=request.user)
    channel = get_object_or_404(Channel, workspace=workspace, slug=channel_slug)

    if not channel.is_member(request.user):
        messages.error(request, "You don't have access to that channel.")
        return redirect("workspace_detail", slug=workspace.slug)

    all_channels = [c for c in workspace.channels.filter(is_dm=False) if c.is_member(request.user)]
    history = channel.messages.select_related("user").order_by("created_at")[:200]
    channel_form = ChannelForm()

    return render(
        request,
        "core/channel_detail.html",
        {
            "workspace": workspace,
            "membership": membership,
            "channel": channel,
            "all_channels": all_channels,
            "history": history,
            "channel_form": channel_form,
        },
    )
