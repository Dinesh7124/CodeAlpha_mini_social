from django.contrib import admin
from .models import (
    Profile, Post, Comment, Like, Reaction, Follow,
    Notification, Story, SavedPost, PasswordResetOTP,
    FriendRequest, Friendship, Conversation, Message
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_banned', 'created_at')
    list_filter = ('role', 'is_banned')
    search_fields = ('user__username', 'user__email', 'phone_number')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'privacy', 'created_at')
    list_filter = ('privacy', 'created_at')
    search_fields = ('author__username', 'content')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'post', 'parent', 'created_at')
    search_fields = ('author__username', 'content')


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'created_at')


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'reaction_type', 'created_at')
    list_filter = ('reaction_type',)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower', 'following', 'created_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'sender', 'notif_type', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read')


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'caption', 'created_at')


@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'created_at')


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'otp', 'is_used', 'created_at')


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_user', 'to_user', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('id', 'user1', 'user2', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user1', 'user2', 'created_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'text', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('sender__username', 'text')