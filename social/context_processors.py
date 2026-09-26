from .models import Conversation, Message, Notification
from django.db.models import Q


def unread_counts(request):
    """Automatically add unread counts to every template context."""
    if not request.user.is_authenticated:
        return {'unread_count': 0, 'unread_messages': 0}

    notif_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    msg_count = Message.objects.filter(
        conversation__in=Conversation.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        ),
        is_read=False
    ).exclude(sender=request.user).count()

    return {
        'unread_count': notif_count,
        'unread_messages': msg_count,
    }