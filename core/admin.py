from django.contrib import admin

from .models import Workspace, Membership, Channel, ChannelMembership, Message

admin.site.register(Workspace)
admin.site.register(Membership)
admin.site.register(Channel)
admin.site.register(ChannelMembership)
admin.site.register(Message)
