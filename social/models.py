from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta


# ==================== PROFILE ====================
class Profile(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('moderator', 'Moderator'),
        ('admin', 'Admin'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, max_length=300)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    cover = models.ImageField(upload_to='covers/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    is_banned = models.BooleanField(default=False)
    ban_reason = models.TextField(blank=True)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

    @property
    def followers_count(self):
        return self.user.followers.count()

    @property
    def following_count(self):
        return self.user.following.count()

    @property
    def is_admin(self):
        return self.role == 'admin' or self.user.is_superuser

    @property
    def is_moderator(self):
        return self.role in ['moderator', 'admin'] or self.user.is_superuser

    @property
    def can_moderate(self):
        return self.is_moderator


# ==================== PASSWORD RESET OTP ====================
class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_otps')
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() - self.created_at > timedelta(minutes=10)

    def __str__(self):
        return f"{self.user.username} - {self.otp}"


# ==================== POST ====================
class Post(models.Model):
    PRIVACY = (
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Only Me'),
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField(max_length=1000, blank=True)
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    video = models.FileField(upload_to='videos/', blank=True, null=True)
    privacy = models.CharField(max_length=10, choices=PRIVACY, default='public')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author.username}: {self.content[:40]}"

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.count()

    @property
    def reactions_count(self):
        return self.reactions.count()

    @property
    def top_level_comments(self):
        return self.comments.filter(parent__isnull=True)


# ==================== COMMENT ====================
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username}: {self.content[:30]}"


# ==================== LIKE ====================
class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


# ==================== REACTION ====================
class Reaction(models.Model):
    REACTION_TYPES = (
        ('like', 'Like'),
        ('love', 'Love'),
        ('haha', 'Haha'),
        ('wow', 'Wow'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reactions')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


# ==================== FOLLOW ====================
class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')


# ==================== NOTIFICATION ====================
class Notification(models.Model):
    NOTIF_TYPES = (
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('follow', 'Follow'),
        ('friend_request', 'Friend Request'),
        ('friend_accept', 'Friend Accept'),
        ('message', 'Message'),
    )
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


# ==================== STORY ====================
class Story(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    image = models.ImageField(upload_to='stories/')
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_active(self):
        return timezone.now() - self.created_at < timedelta(hours=24)


# ==================== SAVED POST ====================
class SavedPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_posts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']


# ==================== FRIEND REQUEST ====================
class FriendRequest(models.Model):
    STATUS = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    from_user = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.status})"


# ==================== FRIENDSHIP ====================
class Friendship(models.Model):
    user1 = models.ForeignKey(User, related_name='friends1', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='friends2', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')

    @staticmethod
    def are_friends(a, b):
        return Friendship.objects.filter(
            Q(user1=a, user2=b) | Q(user1=b, user2=a)
        ).exists()


# ==================== CONVERSATION + MESSAGE ====================
class Conversation(models.Model):
    user1 = models.ForeignKey(User, related_name='conv1', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='conv2', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')

    @staticmethod
    def get_or_create_between(a, b):
        u1, u2 = (a, b) if a.id < b.id else (b, a)
        obj, _ = Conversation.objects.get_or_create(user1=u1, user2=u2)
        return obj


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to='chat/', blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.text[:30]}"


# ==================== POST SHARE ====================
class PostShare(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_posts')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_shares')
    message = models.TextField(blank=True, max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender.username} → {self.recipient.username}"


# ==================== STORY REACTION ====================
class StoryReaction(models.Model):
    REACTIONS = (
        ('love', '❤️'), ('haha', '😂'), ('wow', '😮'),
        ('sad', '😢'), ('fire', '🔥'), ('clap', '👏'),
    )
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='story_reactions')
    reaction = models.CharField(max_length=10, choices=REACTIONS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'user')


# ==================== BLOCK USER ====================
class Block(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocking')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"

    @staticmethod
    def is_blocked(user_a, user_b):
        return Block.objects.filter(
            Q(blocker=user_a, blocked=user_b) | Q(blocker=user_b, blocked=user_a)
        ).exists()


# ==================== REPORT CONTENT ====================
class Report(models.Model):
    REASONS = (
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('hate', 'Hate Speech'),
        ('violence', 'Violence'),
        ('nudity', 'Nudity'),
        ('false_info', 'False Information'),
        ('other', 'Other'),
    )
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='reports_received')
    reason = models.CharField(max_length=20, choices=REASONS)
    details = models.TextField(blank=True, max_length=500)
    is_reviewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


# ==================== HASHTAG ====================
class Hashtag(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    post_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-post_count']

    def __str__(self):
        return f"#{self.name} ({self.post_count})"


# ==================== PROFILE VIEW ====================
class ProfileView(models.Model):
    viewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_views_made')
    viewed = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_views_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.viewer.username} → {self.viewed.username}"


# ==================== SIGNAL ====================
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)