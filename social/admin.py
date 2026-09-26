from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from .models import (
    Profile, Post, Comment, Like, Reaction, Follow,
    Notification, Story, SavedPost, PasswordResetOTP,
    FriendRequest, Friendship, Conversation, Message
)


# ============================================================
# SHARED HELPERS
# ============================================================

class TimeStampedAdmin(admin.ModelAdmin):
    """Base admin with common read-only timestamp field."""
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 25
    show_full_result_count = True


def user_link(obj):
    """Render a clickable link to the user change page."""
    if not obj:
        return '—'
    url = reverse('admin:auth_user_change', args=[obj.pk])
    return format_html('<a href="{}">{}</a>', url, obj.username)


def avatar_preview(obj, size=36):
    """Render a small circular avatar preview."""
    if not obj or not getattr(obj, 'avatar', None):
        return '—'
    return format_html(
        '<img src="{}" style="width:{}px;height:{}px;border-radius:50%;'
        'object-fit:cover;border:1px solid #ddd;" />',
        obj.avatar.url, size, size
    )
avatar_preview.short_description = 'Avatar'


# ============================================================
# PROFILE
# ============================================================

@admin.register(Profile)
class ProfileAdmin(TimeStampedAdmin):
    list_display = ('user_link', 'role', 'is_banned', 'posts_count', 'created_at')
    list_filter = ('role', 'is_banned', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name',
                     'user__last_name', 'phone_number', 'bio')
    list_select_related = ('user',)
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at') if hasattr(Profile, 'updated_at') else ('created_at',)
    actions = ('ban_users', 'unban_users', 'promote_to_moderator', 'demote_to_user')

    fieldsets = (
        ('Account', {
            'fields': ('user', 'role', 'is_banned')
        }),
        ('Personal', {
            'fields': ('bio', 'phone_number', 'avatar', 'cover_image'),
            'classes': ('collapse',),
        }),
        ('Meta', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='User', ordering='user__username')
    def user_link(self, obj):
        return user_link(obj.user)

    @admin.display(description='Posts')
    def posts_count(self, obj):
        return getattr(obj, 'posts_count', obj.user.post_set.count())

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').annotate(
            posts_count=Count('user__post', distinct=True)
        )

    # ---- Bulk actions ----
    @admin.action(description='🚫 Ban selected profiles')
    def ban_users(self, request, queryset):
        updated = queryset.update(is_banned=True)
        self.message_user(request, f'{updated} profile(s) banned.')

    @admin.action(description='✅ Unban selected profiles')
    def unban_users(self, request, queryset):
        updated = queryset.update(is_banned=False)
        self.message_user(request, f'{updated} profile(s) unbanned.')

    @admin.action(description='🛡️ Promote to Moderator')
    def promote_to_moderator(self, request, queryset):
        updated = queryset.update(role='moderator')
        self.message_user(request, f'{updated} profile(s) promoted.')

    @admin.action(description='👤 Demote to User')
    def demote_to_user(self, request, queryset):
        updated = queryset.update(role='user')
        self.message_user(request, f'{updated} profile(s) demoted.')


# ============================================================
# POST + INLINES
# ============================================================

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ('author', 'content', 'parent', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('author',)
    show_change_link = True
    classes = ('collapse',)


class ReactionInline(admin.TabularInline):
    model = Reaction
    extra = 0
    fields = ('user', 'reaction_type', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('user',)
    classes = ('collapse',)


@admin.register(Post)
class PostAdmin(TimeStampedAdmin):
    list_display = ('id', 'author_link', 'short_content', 'privacy',
                    'likes_count', 'comments_count', 'created_at')
    list_filter = ('privacy', 'created_at')
    search_fields = ('author__username', 'author__email', 'content')
    list_select_related = ('author',)
    autocomplete_fields = ('author',)
    inlines = (CommentInline, ReactionInline)
    actions = ('make_public', 'make_private', 'delete_selected_safe')
    list_per_page = 30

    fieldsets = (
        ('Content', {
            'fields': ('author', 'content', 'image', 'privacy')
        }),
        ('Meta', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Author', ordering='author__username')
    def author_link(self, obj):
        return user_link(obj.author)

    @admin.display(description='Content')
    def short_content(self, obj):
        text = (obj.content or '')[:80]
        return f'{text}…' if len(obj.content or '') > 80 else text or '—'

    @admin.display(description='❤️ Likes')
    def likes_count(self, obj):
        return getattr(obj, 'likes_count', 0)

    @admin.display(description='💬 Comments')
    def comments_count(self, obj):
        return getattr(obj, 'comments_count', 0)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('author').annotate(
            likes_count=Count('reaction', distinct=True),
            comments_count=Count('comment', distinct=True),
        )

    @admin.action(description='🌍 Make selected posts public')
    def make_public(self, request, queryset):
        updated = queryset.update(privacy='public')
        self.message_user(request, f'{updated} post(s) set to public.')

    @admin.action(description='🔒 Make selected posts private')
    def make_private(self, request, queryset):
        updated = queryset.update(privacy='private')
        self.message_user(request, f'{updated} post(s) set to private.')


# ============================================================
# COMMENT
# ============================================================

@admin.register(Comment)
class CommentAdmin(TimeStampedAdmin):
    list_display = ('id', 'author_link', 'post_link', 'short_content',
                    'parent', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('author__username', 'content', 'post__id')
    list_select_related = ('author', 'post', 'parent')
    autocomplete_fields = ('author', 'post', 'parent')
    list_per_page = 30

    @admin.display(description='Author', ordering='author__username')
    def author_link(self, obj):
        return user_link(obj.author)

    @admin.display(description='Post')
    def post_link(self, obj):
        if not obj.post:
            return '—'
        url = reverse('admin:social_post_change', args=[obj.post.pk])
        return format_html('<a href="{}">Post #{}</a>', url, obj.post.pk)

    @admin.display(description='Comment')
    def short_content(self, obj):
        return (obj.content or '')[:60] + ('…' if len(obj.content or '') > 60 else '')


# ============================================================
# LIKE / REACTION
# ============================================================

@admin.register(Like)
class LikeAdmin(TimeStampedAdmin):
    list_display = ('id', 'user_link', 'post_link', 'created_at')
    list_select_related = ('user', 'post')
    autocomplete_fields = ('user', 'post')
    list_filter = ('created_at',)

    @admin.display(description='User', ordering='user__username')
    def user_link(self, obj):
        return user_link(obj.user)

    @admin.display(description='Post')
    def post_link(self, obj):
        return format_html('<a href="{}">Post #{}</a>',
                           reverse('admin:social_post_change', args=[obj.post.pk]),
                           obj.post.pk) if obj.post else '—'


@admin.register(Reaction)
class ReactionAdmin(TimeStampedAdmin):
    list_display = ('id', 'user_link', 'post_link', 'reaction_type', 'created_at')
    list_filter = ('reaction_type', 'created_at')
    list_select_related = ('user', 'post')
    autocomplete_fields = ('user', 'post')

    @admin.display(description='User', ordering='user__username')
    def user_link(self, obj):
        return user_link(obj.user)

    @admin.display(description='Post')
    def post_link(self, obj):
        return format_html('<a href="{}">Post #{}</a>',
                           reverse('admin:social_post_change', args=[obj.post.pk]),
                           obj.post.pk) if obj.post else '—'


# ============================================================
# FOLLOW
# ============================================================

@admin.register(Follow)
class FollowAdmin(TimeStampedAdmin):
    list_display = ('id', 'follower_link', 'following_link', 'created_at')
    search_fields = ('follower__username', 'following__username')
    list_select_related = ('follower', 'following')
    autocomplete_fields = ('follower', 'following')
    list_filter = ('created_at',)

    @admin.display(description='Follower', ordering='follower__username')
    def follower_link(self, obj):
        return user_link(obj.follower)

    @admin.display(description='Following', ordering='following__username')
    def following_link(self, obj):
        return user_link(obj.following)


# ============================================================
# NOTIFICATION
# ============================================================

@admin.register(Notification)
class NotificationAdmin(TimeStampedAdmin):
    list_display = ('id', 'recipient_link', 'sender_link', 'notif_type',
                    'is_read_display', 'created_at')
    list_filter = ('notif_type', 'is_read', 'created_at')
    search_fields = ('recipient__username', 'sender__username')
    list_select_related = ('recipient', 'sender')
    autocomplete_fields = ('recipient', 'sender')
    actions = ('mark_read', 'mark_unread')
    list_per_page = 40

    @admin.display(description='Recipient', ordering='recipient__username')
    def recipient_link(self, obj):
        return user_link(obj.recipient)

    @admin.display(description='Sender', ordering='sender__username')
    def sender_link(self, obj):
        return user_link(obj.sender)

    @admin.display(description='Read', boolean=True)
    def is_read_display(self, obj):
        return obj.is_read

    @admin.action(description='✅ Mark as read')
    def mark_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notification(s) marked as read.')

    @admin.action(description='📩 Mark as unread')
    def mark_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} notification(s) marked as unread.')


# ============================================================
# STORY
# ============================================================

@admin.register(Story)
class StoryAdmin(TimeStampedAdmin):
    list_display = ('id', 'author_link', 'caption', 'is_expired', 'created_at')
    search_fields = ('author__username', 'caption')
    list_select_related = ('author',)
    autocomplete_fields = ('author',)
    list_filter = ('created_at',)
    actions = ('delete_expired',)

    @admin.display(description='Author', ordering='author__username')
    def author_link(self, obj):
        return user_link(obj.author)

    @admin.display(description='Expired?', boolean=True)
    def is_expired(self, obj):
        return obj.created_at < timezone.now() - timedelta(hours=24)

    @admin.action(description='🗑️ Delete expired stories (>24h)')
    def delete_expired(self, request, queryset):
        cutoff = timezone.now() - timedelta(hours=24)
        deleted, _ = queryset.filter(created_at__lt=cutoff).delete()
        self.message_user(request, f'{deleted} expired story(s) deleted.')


# ============================================================
# SAVED POST
# ============================================================

@admin.register(SavedPost)
class SavedPostAdmin(TimeStampedAdmin):
    list_display = ('id', 'user_link', 'post_link', 'created_at')
    list_select_related = ('user', 'post')
    autocomplete_fields = ('user', 'post')
    search_fields = ('user__username',)
    list_filter = ('created_at',)

    @admin.display(description='User', ordering='user__username')
    def user_link(self, obj):
        return user_link(obj.user)

    @admin.display(description='Post')
    def post_link(self, obj):
        return format_html('<a href="{}">Post #{}</a>',
                           reverse('admin:social_post_change', args=[obj.post.pk]),
                           obj.post.pk) if obj.post else '—'


# ============================================================
# PASSWORD RESET OTP
# ============================================================

@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(TimeStampedAdmin):
    list_display = ('id', 'user_link', 'otp_masked', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'user__email')
    list_select_related = ('user',)
    autocomplete_fields = ('user',)
    actions = ('invalidate_otps',)

    @admin.display(description='User', ordering='user__username')
    def user_link(self, obj):
        return user_link(obj.user)

    @admin.display(description='OTP')
    def otp_masked(self, obj):
        # Mask OTP for security — don't show full codes in list view
        code = str(obj.otp or '')
        return f'{"*" * (len(code) - 2)}{code[-2:]}' if len(code) > 2 else '****'

    @admin.action(description='🚫 Invalidate selected OTPs')
    def invalidate_otps(self, request, queryset):
        updated = queryset.update(is_used=True)
        self.message_user(request, f'{updated} OTP(s) invalidated.')


# ============================================================
# FRIEND REQUEST
# ============================================================

@admin.register(FriendRequest)
class FriendRequestAdmin(TimeStampedAdmin):
    list_display = ('id', 'from_user_link', 'to_user_link', 'status',
                    'is_pending_display', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('from_user__username', 'to_user__username')
    list_select_related = ('from_user', 'to_user')
    autocomplete_fields = ('from_user', 'to_user')
    actions = ('accept_requests', 'reject_requests')

    @admin.display(description='From', ordering='from_user__username')
    def from_user_link(self, obj):
        return user_link(obj.from_user)

    @admin.display(description='To', ordering='to_user__username')
    def to_user_link(self, obj):
        return user_link(obj.to_user)

    @admin.display(description='Pending?', boolean=True)
    def is_pending_display(self, obj):
        return obj.status == 'pending'

    @admin.action(description='✅ Accept selected requests')
    def accept_requests(self, request, queryset):
        updated = queryset.update(status='accepted')
        self.message_user(request, f'{updated} request(s) accepted.')

    @admin.action(description='❌ Reject selected requests')
    def reject_requests(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} request(s) rejected.')


# ============================================================
# FRIENDSHIP
# ============================================================

@admin.register(Friendship)
class FriendshipAdmin(TimeStampedAdmin):
    list_display = ('id', 'user1_link', 'user2_link', 'created_at')
    search_fields = ('user1__username', 'user2__username')
    list_select_related = ('user1', 'user2')
    autocomplete_fields = ('user1', 'user2')

    @admin.display(description='User 1', ordering='user1__username')
    def user1_link(self, obj):
        return user_link(obj.user1)

    @admin.display(description='User 2', ordering='user2__username')
    def user2_link(self, obj):
        return user_link(obj.user2)


# ============================================================
# CONVERSATION + MESSAGE INLINE
# ============================================================

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ('sender', 'text', 'is_read', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('sender',)
    show_change_link = True
    classes = ('collapse',)
    max_num = 20


@admin.register(Conversation)
class ConversationAdmin(TimeStampedAdmin):
    list_display = ('id', 'user1_link', 'user2_link',
                    'messages_count', 'last_message_at', 'created_at')
    search_fields = ('user1__username', 'user2__username')
    list_select_related = ('user1', 'user2')
    autocomplete_fields = ('user1', 'user2')
    inlines = (MessageInline,)
    list_filter = ('created_at',)

    @admin.display(description='User 1', ordering='user1__username')
    def user1_link(self, obj):
        return user_link(obj.user1)

    @admin.display(description='User 2', ordering='user2__username')
    def user2_link(self, obj):
        return user_link(obj.user2)

    @admin.display(description='💬 Messages')
    def messages_count(self, obj):
        return getattr(obj, 'messages_count', 0)

    @admin.display(description='Last message', ordering='last_message_at')
    def last_message_at(self, obj):
        return getattr(obj, 'last_message_at', None) or '—'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user1', 'user2').annotate(
            messages_count=Count('message', distinct=True),
        )


# ============================================================
# MESSAGE
# ============================================================

@admin.register(Message)
class MessageAdmin(TimeStampedAdmin):
    list_display = ('id', 'conversation_link', 'sender_link',
                    'short_text', 'is_read_display', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'text', 'conversation__id')
    list_select_related = ('sender', 'conversation')
    autocomplete_fields = ('sender', 'conversation')
    actions = ('mark_read', 'mark_unread')
    list_per_page = 50

    @admin.display(description='Conversation')
    def conversation_link(self, obj):
        if not obj.conversation:
            return '—'
        url = reverse('admin:social_conversation_change', args=[obj.conversation.pk])
        return format_html('<a href="{}">#{}</a>', url, obj.conversation.pk)

    @admin.display(description='Sender', ordering='sender__username')
    def sender_link(self, obj):
        return user_link(obj.sender)

    @admin.display(description='Message')
    def short_text(self, obj):
        return (obj.text or '')[:60] + ('…' if len(obj.text or '') > 60 else '')

    @admin.display(description='Read', boolean=True)
    def is_read_display(self, obj):
        return obj.is_read

    @admin.action(description='✅ Mark as read')
    def mark_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} message(s) marked as read.')

    @admin.action(description='📩 Mark as unread')
    def mark_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} message(s) marked as unread.')


# ============================================================
# ADMIN SITE BRANDING
# ============================================================

admin.site.site_header = '⚡ MiniSocial Administration'
admin.site.site_title = 'MiniSocial Admin'
admin.site.index_title = 'Welcome to MiniSocial Control Center'