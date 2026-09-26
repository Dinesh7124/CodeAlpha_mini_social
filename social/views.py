# ============ IMPORTS ============
import os
import random
import resend
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
from django.contrib import messages

from .models import (
    Post, Comment, Like, Follow, Notification,
    Message, Story, SavedPost, Reaction, Profile,
    PasswordResetOTP, FriendRequest, Friendship, Conversation,
    PostShare, StoryReaction, Block, Report, Hashtag, ProfileView,
    Collection, CollectionItem, PostDraft  # ✅ NAYE
)

@login_required
def story_viewer(request, story_id):
    """Full-screen story viewer."""
    cutoff = timezone.now() - timedelta(hours=24)
    stories = Story.objects.filter(
        created_at__gte=cutoff
    ).select_related('author').order_by('-created_at')

    return render(request, 'social/story_viewer.html', {
        'stories': stories,
        'story_id': story_id,
    })

# ============ API: FRIENDS LIST ============
@login_required
def api_friends(request):
    """Return list of friends for share modal."""
    friend_ids = get_friend_ids(request.user)
    friends = User.objects.filter(id__in=friend_ids).select_related('profile')

    return JsonResponse({
        'friends': [
            {
                'id': f.id,
                'username': f.username,
                'full_name': f.get_full_name() or f.username,
                'avatar': f.profile.avatar.url if f.profile.avatar else None,
            } for f in friends
        ]
    })


@login_required
def friends_list(request):
    """Show all friends of the current user."""
    friend_ids = get_friend_ids(request.user)
    friends = User.objects.filter(id__in=friend_ids).select_related('profile').order_by('username')

    return render(request, 'social/friends_list.html', {
        'friends': friends,
        'total_friends': friends.count(),
        'unread_count': _unread(request.user),
    })

# ============ HELPERS ============
def get_friend_ids(user):
    ids = set()
    for f in Friendship.objects.filter(Q(user1=user) | Q(user2=user)):
        ids.add(f.user2_id if f.user1_id == user.id else f.user1_id)
    return ids


def _get_reaction_counts(post):
    counts = {}
    for row in Reaction.objects.filter(post=post).values('reaction_type').annotate(count=Count('id')):
        counts[row['reaction_type']] = row['count']
    return counts


def _unread(user):
    if not user.is_authenticated:
        return 0
    return user.notifications.filter(is_read=False).count()

# ============ POST DRAFTS ============
@login_required
@require_POST
def save_draft(request):
    """Save current post as draft."""
    content = request.POST.get('content', '').strip()
    image = request.FILES.get('image')
    video = request.FILES.get('video')

    if not content and not image and not video:
        return JsonResponse({'error': 'Nothing to save'}, status=400)

    # Only 1 draft per user - delete old, create new
    PostDraft.objects.filter(author=request.user).delete()

    draft = PostDraft.objects.create(
        author=request.user,
        content=content,
        image=image,
        video=video
    )

    return JsonResponse({
        'status': 'ok',
        'draft_id': draft.id,
        'msg': 'Draft saved!'
    })


@login_required
def get_draft(request):
    """Get current user's draft (if any)."""
    draft = PostDraft.objects.filter(author=request.user).first()

    if not draft:
        return JsonResponse({'draft': None})

    return JsonResponse({
        'draft': {
            'id': draft.id,
            'content': draft.content,
            'image': draft.image.url if draft.image else None,
            'video': draft.video.url if draft.video else None,
            'updated_at': draft.updated_at.strftime('%b %d, %H:%M'),
        }
    })


@login_required
@require_POST
def delete_draft(request, draft_id):
    """Delete a draft."""
    draft = get_object_or_404(PostDraft, id=draft_id, author=request.user)
    draft.delete()
    return JsonResponse({'status': 'ok', 'msg': 'Draft deleted'})



# ============ RESEND CONFIG ============
resend.api_key = os.environ.get('RESEND_API_KEY', '')
FROM_EMAIL = 'MiniSocial <onboarding@resend.dev>'


def send_email_via_resend(to_email, subject, html_body):
    if not resend.api_key:
        print(f'⚠️ RESEND_API_KEY not set. Skipping email to {to_email}')
        return False
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        })
        return True
    except Exception as e:
        print(f'❌ Email send failed: {e}')
        return False


# ============ AUTH ============
def login_view(request):
    if request.user.is_authenticated:
        return redirect('feed')

    if request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = None
        if '@' in username_or_email:
            u = User.objects.filter(email__iexact=username_or_email).first()
            if u:
                user = authenticate(request, username=u.username, password=password)
        else:
            user = authenticate(request, username=username_or_email, password=password)

        if user is not None:
            if user.profile.is_banned:
                return render(request, 'social/login.html', {
                    'error': f'Your account is banned. Reason: {user.profile.ban_reason}'
                })
            login(request, user)
            next_url = request.GET.get('next', 'feed')
            return redirect(next_url)
        else:
            return render(request, 'social/login.html', {
                'error': 'Invalid username/email or password.',
            })

    return render(request, 'social/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('feed')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        password2 = request.POST.get('password2', '').strip()

        errors = []
        if not first_name:
            errors.append('First name is required.')
        if not email:
            errors.append('Email is required.')
        if not phone:
            errors.append('Phone number is required.')
        if not password:
            errors.append('Password is required.')
        if password != password2:
            errors.append('Passwords do not match.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if email and User.objects.filter(email__iexact=email).exists():
            errors.append('This email is already registered.')
        if phone and Profile.objects.filter(phone_number=phone).exists():
            errors.append('This phone number is already registered.')

        if errors:
            return render(request, 'social/login.html', {
                'error': ' | '.join(errors),
                'show_register': True,
                'form_data': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                }
            })

        base_username = first_name.lower().replace(' ', '')
        username = base_username + str(random.randint(1000, 9999))
        while User.objects.filter(username=username).exists():
            username = base_username + str(random.randint(1000, 9999))

        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name,
        )
        user.profile.phone_number = phone
        user.profile.save()

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
            <h2 style="color:#6366f1;">Welcome to MiniSocial, {first_name}! 🎉</h2>
            <p>Your account has been created successfully.</p>
            <div style="background:#f4f6f9;padding:15px;border-radius:8px;margin:20px 0;">
                <h3 style="margin-top:0;">Your Login Details</h3>
                <p><strong>Username:</strong> {username}</p>
                <p><strong>Email:</strong> {email}</p>
            </div>
            <p>Happy connecting!<br><strong>MiniSocial Team</strong></p>
        </div>
        """
        send_email_via_resend(email, 'Welcome to MiniSocial — Your Account Details', html_body)

        login(request, user)
        return redirect('feed')

    return render(request, 'social/login.html', {'show_register': True})


def logout_view(request):
    logout(request)
    return redirect('login')


# ============ FORGOT PASSWORD ============
def forgot_password_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        user = None
        if '@' in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
        else:
            profile = Profile.objects.filter(phone_number=identifier).first()
            if profile:
                user = profile.user

        if not user:
            return render(request, 'social/forgot_password.html', {
                'error': 'No account found with this email/phone.'
            })

        otp_code = str(random.randint(100000, 999999))
        PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)
        PasswordResetOTP.objects.create(user=user, otp=otp_code)

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
            <h2 style="color:#6366f1;">Password Reset OTP</h2>
            <div style="background:#f4f6f9;padding:20px;border-radius:8px;margin:20px 0;text-align:center;">
                <h1 style="font-size:36px;letter-spacing:8px;color:#6366f1;">{otp_code}</h1>
            </div>
            <p>Valid for 10 minutes.</p>
        </div>
        """
        send_email_via_resend(user.email, 'MiniSocial — Password Reset OTP', html_body)

        return render(request, 'social/forgot_password.html', {
            'step': 'verify',
            'identifier': identifier,
            'dev_otp': otp_code if settings.DEBUG else None,
            'info': f'OTP sent to {user.email}.'
        })

    return render(request, 'social/forgot_password.html')


def verify_otp_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        otp_entered = request.POST.get('otp', '').strip()

        user = None
        if '@' in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
        else:
            profile = Profile.objects.filter(phone_number=identifier).first()
            if profile:
                user = profile.user

        if not user:
            return render(request, 'social/forgot_password.html', {'error': 'User not found.'})

        otp_record = PasswordResetOTP.objects.filter(
            user=user, otp=otp_entered, is_used=False
        ).order_by('-created_at').first()

        if not otp_record or otp_record.is_expired():
            return render(request, 'social/forgot_password.html', {
                'step': 'verify', 'identifier': identifier,
                'error': 'Invalid or expired OTP.'
            })

        otp_record.is_used = True
        otp_record.save()

        return render(request, 'social/forgot_password.html', {
            'step': 'reset', 'identifier': identifier,
            'info': 'OTP verified! Set your new password.'
        })

    return redirect('forgot_password')


def reset_password_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if new_password != confirm_password:
            return render(request, 'social/forgot_password.html', {
                'step': 'reset', 'identifier': identifier,
                'error': 'Passwords do not match.'
            })
        if len(new_password) < 6:
            return render(request, 'social/forgot_password.html', {
                'step': 'reset', 'identifier': identifier,
                'error': 'Password must be at least 6 characters.'
            })

        user = None
        if '@' in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
        else:
            profile = Profile.objects.filter(phone_number=identifier).first()
            if profile:
                user = profile.user

        if user:
            user.set_password(new_password)
            user.save()
            return render(request, 'social/login.html', {
                'info': 'Password reset successful! Please login.'
            })

    return redirect('forgot_password')


# ============ FEED ============
@login_required
def feed(request):
    my_friend_ids = get_friend_ids(request.user)

    posts_qs = Post.objects.filter(
        Q(privacy='public') |
        Q(author=request.user) |
        Q(privacy='friends', author_id__in=my_friend_ids)
    ).select_related('author').prefetch_related(
        'comments__author', 'comments__replies__author', 'likes', 'reactions'
    ).distinct().order_by('-created_at')

    paginator = Paginator(posts_qs, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    liked_ids = set(request.user.likes.values_list('post_id', flat=True))
    saved_ids = set(request.user.saved_posts.values_list('post_id', flat=True))
    my_reactions = {r.post_id: r.reaction_type for r in request.user.reactions.all()}

    cutoff = timezone.now() - timedelta(hours=24)
    active_stories = Story.objects.filter(
        created_at__gte=cutoff
    ).select_related('author').order_by('-created_at')[:20]

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('social/_post_list.html', {
            'posts': page_obj,
            'liked_ids': liked_ids,
            'saved_ids': saved_ids,
            'my_reactions': my_reactions,
        }, request=request)
        return JsonResponse({'html': html, 'has_next': page_obj.has_next()})

    return render(request, 'social/feed.html', {
        'posts': page_obj,
        'liked_ids': liked_ids,
        'saved_ids': saved_ids,
        'my_reactions': my_reactions,
        'unread_count': _unread(request.user),
        'active_stories': active_stories,
        'has_next': page_obj.has_next(),
    })


# ============ PROFILE ============
@login_required
def profile(request, username):
    user_obj = get_object_or_404(User, username=username)

    # Block check
    if Block.is_blocked(request.user, user_obj):
        return render(request, 'social/blocked_profile.html', {
            'blocked_user': user_obj,
            'unread_count': _unread(request.user),
        })

    # Track profile view
    track_profile_view(request.user, user_obj)

    posts = user_obj.posts.all()

    if request.user != user_obj and not Friendship.are_friends(request.user, user_obj):
        posts = posts.exclude(privacy__in=['private', 'friends'])

    is_own = (request.user == user_obj)
    is_following = Follow.objects.filter(follower=request.user, following=user_obj).exists()

    friend_status = None
    pending_req = None
    if not is_own:
        if Friendship.are_friends(request.user, user_obj):
            friend_status = 'friends'
        else:
            sent = FriendRequest.objects.filter(from_user=request.user, to_user=user_obj, status='pending').first()
            received = FriendRequest.objects.filter(from_user=user_obj, to_user=request.user, status='pending').first()
            if sent:
                friend_status = 'sent'
            elif received:
                friend_status = 'received'
                pending_req = received

    return render(request, 'social/profile.html', {
        'profile_user': user_obj,
        'posts': posts,
        'is_following': is_following,
        'is_own': is_own,
        'friend_status': friend_status,
        'pending_req': pending_req,
        'unread_count': _unread(request.user),
    })

@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        profile.bio = request.POST.get('bio', '').strip()
        profile.location = request.POST.get('location', '').strip()
        website = request.POST.get('website', '').strip()
        if website and not website.startswith(('http://', 'https://')):
            website = 'https://' + website
        profile.website = website
        if request.FILES.get('avatar'):
            profile.avatar = request.FILES['avatar']
        if request.FILES.get('cover'):
            profile.cover = request.FILES['cover']
        profile.save()
        return redirect('profile', username=request.user.username)

    return render(request, 'social/edit_profile.html', {
        'profile': profile,
        'unread_count': _unread(request.user),
    })


# ============ POSTS ============
@login_required
@require_POST
def create_post(request):
    content = request.POST.get('content', '').strip()
    image = request.FILES.get('image')
    video = request.FILES.get('video')
    privacy = request.POST.get('privacy', 'public')

    if privacy not in ['public', 'friends', 'private']:
        privacy = 'public'

    if content or image or video:
        Post.objects.create(
            author=request.user, content=content,
            image=image, video=video, privacy=privacy
        )
        # Delete draft after successful post
        PostDraft.objects.filter(author=request.user).delete()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Empty post'}, status=400)


@login_required
@require_POST
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    content = request.POST.get('content', '').strip()
    if content:
        post.content = content
        post.save()
        return JsonResponse({'success': True, 'content': post.content})
    return JsonResponse({'error': 'Empty content'}, status=400)


@login_required
@require_POST
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    post.delete()
    return JsonResponse({'success': True})


# ============ LIKE ============
@login_required
@require_POST
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        return JsonResponse({'liked': False, 'count': post.likes_count})

    if post.author != request.user:
        Notification.objects.create(
            recipient=post.author, sender=request.user,
            notif_type='like', post=post
        )
    return JsonResponse({'liked': True, 'count': post.likes_count})


# ============ REACTION ============
@login_required
@require_POST
def toggle_reaction(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    reaction_type = request.POST.get('reaction', 'like')

    if reaction_type not in ['like', 'love', 'haha', 'wow', 'sad', 'angry']:
        reaction_type = 'like'

    existing = Reaction.objects.filter(user=request.user, post=post).first()

    if existing:
        if existing.reaction_type == reaction_type:
            existing.delete()
            return JsonResponse({
                'removed': True, 'reaction': None,
                'counts': _get_reaction_counts(post),
                'total': post.reactions_count,
            })
        else:
            existing.reaction_type = reaction_type
            existing.save()
            return JsonResponse({
                'removed': False, 'reaction': reaction_type,
                'counts': _get_reaction_counts(post),
                'total': post.reactions_count,
            })
    else:
        Reaction.objects.create(user=request.user, post=post, reaction_type=reaction_type)
        if post.author != request.user:
            Notification.objects.create(
                recipient=post.author, sender=request.user,
                notif_type='like', post=post
            )
        return JsonResponse({
            'removed': False, 'reaction': reaction_type,
            'counts': _get_reaction_counts(post),
            'total': post.reactions_count,
        })


# ============ COMMENT ============
@login_required
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    content = request.POST.get('content', '').strip()
    parent_id = request.POST.get('parent_id')
    parent = Comment.objects.filter(id=parent_id).first() if parent_id else None

    if content:
        comment = Comment.objects.create(
            post=post, author=request.user,
            content=content, parent=parent
        )
        if post.author != request.user:
            Notification.objects.create(
                recipient=post.author, sender=request.user,
                notif_type='comment', post=post
            )
        return JsonResponse({
            'id': comment.id,
            'content': comment.content,
            'author': comment.author.username,
            'author_id': comment.author.id,
            'parent_id': parent_id,
            'created_at': comment.created_at.strftime('%H:%M'),
        })
    return JsonResponse({'error': 'Empty'}, status=400)


@login_required
@require_POST
def delete_comment(request, comment_id):
    c = get_object_or_404(Comment, id=comment_id, author=request.user)
    c.delete()
    return JsonResponse({'status': 'ok'})


# ============ FOLLOW ============
@login_required
@require_POST
def toggle_follow(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return JsonResponse({'error': 'Cannot follow yourself'}, status=400)

    follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        follow.delete()
        return JsonResponse({'following': False, 'followers_count': target.profile.followers_count})

    Notification.objects.create(recipient=target, sender=request.user, notif_type='follow')
    return JsonResponse({'following': True, 'followers_count': target.profile.followers_count})


# ============ FRIEND REQUESTS ============
@login_required
@require_POST
def send_friend_request(request, user_id):
    to_user = get_object_or_404(User, id=user_id)
    if to_user == request.user:
        return JsonResponse({'status': 'error', 'msg': "You cannot send a request to yourself"})
    if Friendship.are_friends(request.user, to_user):
        return JsonResponse({'status': 'error', 'msg': "You are already friends"})

    reverse = FriendRequest.objects.filter(
        from_user=to_user, to_user=request.user, status='pending'
    ).first()
    if reverse:
        reverse.status = 'accepted'
        reverse.save()
        Friendship.objects.get_or_create(user1=to_user, user2=request.user)
        Notification.objects.create(
            recipient=to_user, sender=request.user, notif_type='friend_accept'
        )
        return JsonResponse({'status': 'accepted', 'msg': "You are now friends!"})

    obj, created = FriendRequest.objects.get_or_create(
        from_user=request.user, to_user=to_user,
        defaults={'status': 'pending'}
    )
    if not created:
        return JsonResponse({'status': 'exists', 'msg': "Friend request already sent"})

    Notification.objects.create(
        recipient=to_user, sender=request.user, notif_type='friend_request'
    )
    return JsonResponse({'status': 'sent', 'msg': "Send the Friend Request"})


@login_required
@require_POST
def accept_friend_request(request, req_id):
    fr = get_object_or_404(FriendRequest, id=req_id, to_user=request.user, status='pending')
    fr.status = 'accepted'
    fr.save()
    Friendship.objects.get_or_create(user1=fr.from_user, user2=fr.to_user)
    Notification.objects.create(
        recipient=fr.from_user, sender=request.user, notif_type='friend_accept'
    )
    return JsonResponse({'status': 'accepted'})


@login_required
@require_POST
def reject_friend_request(request, req_id):
    fr = get_object_or_404(FriendRequest, id=req_id, to_user=request.user, status='pending')
    fr.status = 'rejected'
    fr.save()
    return JsonResponse({'status': 'rejected'})


@login_required
def friend_requests_list(request):
    received = FriendRequest.objects.filter(
        to_user=request.user, status='pending'
    ).select_related('from_user')
    sent = FriendRequest.objects.filter(
        from_user=request.user, status='pending'
    ).select_related('to_user')
    return render(request, 'social/friend_requests.html', {
        'received': received,
        'sent': sent,
        'unread_count': _unread(request.user),
    })


# ============ CHAT ============
@login_required
def start_chat(request, user_id):
    other = get_object_or_404(User, id=user_id)
    if not Friendship.are_friends(request.user, other):
        messages.error(request, "Sirf friends ko message kar sakte hain.")
        return redirect('feed')
    conv = Conversation.get_or_create_between(request.user, other)
    return redirect('chat_room', conv_id=conv.id)


@login_required
def chat_room(request, conv_id):
    conv = get_object_or_404(Conversation, id=conv_id)
    if request.user not in [conv.user1, conv.user2]:
        return redirect('feed')

    other = conv.user2 if conv.user1 == request.user else conv.user1
    conv_messages = conv.messages.all()
    conv_messages.filter(sender=other, is_read=False).update(is_read=True)

    return render(request, 'social/chat_room.html', {
        'conv': conv, 'other': other, 'chat_messages': conv_messages,
        'unread_count': _unread(request.user),
    })


@login_required
@require_POST
def chat_send_message(request, conv_id):
    conv = get_object_or_404(Conversation, id=conv_id)
    if request.user not in [conv.user1, conv.user2]:
        return JsonResponse({'status': 'error'}, status=403)

    text = request.POST.get('text', '').strip()
    image = request.FILES.get('image')
    video = request.FILES.get('video')

    if not text and not image and not video:
        return JsonResponse({'status': 'error', 'msg': 'Empty'}, status=400)

    # Save file: image or video (dono image field mein jaayenge)
    media_file = image if image else video

    msg = Message.objects.create(
        conversation=conv,
        sender=request.user,
        text=text,
        image=media_file if media_file else None,
    )

    other = conv.user2 if conv.user1 == request.user else conv.user1
    Notification.objects.create(
        recipient=other, sender=request.user, notif_type='message'
    )

    return JsonResponse({
        'status': 'ok',
        'id': msg.id,
        'text': msg.text,
        'sender': request.user.username,
        'sender_id': request.user.id,
        'time': msg.created_at.strftime('%H:%M'),
        'image': msg.image.url if msg.image else None,
        'is_read': msg.is_read,
    })


@login_required
def get_new_messages(request, conv_id):
    conv = get_object_or_404(Conversation, id=conv_id)
    if request.user not in [conv.user1, conv.user2]:
        return JsonResponse({'messages': []})

    last_id = int(request.GET.get('last_id', 0))
    new_msgs = conv.messages.filter(id__gt=last_id)

    other = conv.user2 if conv.user1 == request.user else conv.user1
    conv.messages.filter(sender=other, is_read=False).update(is_read=True)

    return JsonResponse({
        'messages': [
            {
                'id': m.id,
                'text': m.text,
                'sender': m.sender.username,
                'sender_id': m.sender.id,
                'is_mine': m.sender == request.user,
                'time': m.created_at.strftime('%H:%M'),
                'image': m.image.url if m.image else None,
                'is_read': m.is_read,
            } for m in new_msgs
        ]
    })


@login_required
@require_POST
def chat_typing(request, conv_id):
    """Typing indicator endpoint (client-side handled)."""
    conv = get_object_or_404(Conversation, id=conv_id)
    if request.user not in [conv.user1, conv.user2]:
        return JsonResponse({'status': 'error'}, status=403)
    return JsonResponse({'status': 'ok'})


@login_required
def inbox(request):
    convs = Conversation.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).order_by('-created_at')

    data = []
    for c in convs:
        other = c.user2 if c.user1 == request.user else c.user1
        last = c.messages.last()
        unread = c.messages.filter(sender=other, is_read=False).count()
        data.append({'conv': c, 'other': other, 'last': last, 'unread': unread})

    return render(request, 'social/inbox.html', {
        'data': data,
        'unread_count': _unread(request.user),
    })


# ============ NOTIFICATIONS ============
@login_required
def notifications(request):
    notifs = request.user.notifications.select_related('sender', 'post')[:50]
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'social/notifications.html', {
        'notifications': notifs,
        'unread_count': 0,
    })


@login_required
def unread_count(request):
    return JsonResponse({'count': _unread(request.user)})


# ============ SEARCH ============
@login_required
def search(request):
    query = request.GET.get('q', '').strip()
    users, posts = [], []
    if query:
        users = User.objects.filter(username__icontains=query)[:20]
        posts = Post.objects.filter(
            Q(content__icontains=query) & Q(privacy='public')
        )[:20]
    return render(request, 'social/search.html', {
        'query': query, 'users': users, 'posts': posts,
        'unread_count': _unread(request.user),
    })


# ============ STORIES ============
@login_required
def create_story(request):
    if request.method == 'POST' and request.FILES.get('image'):
        Story.objects.create(
            author=request.user,
            image=request.FILES['image'],
            caption=request.POST.get('caption', '').strip()
        )
        return redirect('feed')
    return render(request, 'social/create_story.html', {
        'unread_count': _unread(request.user),
    })


@login_required
def stories_view(request):
    cutoff = timezone.now() - timedelta(hours=24)
    stories = Story.objects.filter(
        created_at__gte=cutoff
    ).select_related('author').order_by('-created_at')
    return render(request, 'social/stories.html', {
        'stories': stories,
        'unread_count': _unread(request.user),
    })


# ============ SAVED POSTS ============
@login_required
@require_POST
def toggle_save(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    saved, created = SavedPost.objects.get_or_create(user=request.user, post=post)
    if not created:
        saved.delete()
        return JsonResponse({'saved': False})
    return JsonResponse({'saved': True})


@login_required
def saved_posts(request):
    saved = request.user.saved_posts.select_related('post__author')
    return render(request, 'social/saved.html', {
        'saved': saved,
        'unread_count': _unread(request.user),
    })


# ============ SUGGESTIONS ============
@login_required
def suggestions(request):
    following_ids = list(request.user.following.values_list('following_id', flat=True))
    friend_ids = list(get_friend_ids(request.user))

    exclude_ids = set(following_ids + friend_ids + [request.user.id])
    users = User.objects.exclude(id__in=exclude_ids).order_by('-date_joined')[:5]

    return JsonResponse({
        'users': [
            {
                'id': u.id,
                'username': u.username,
                'avatar': u.profile.avatar.url if u.profile.avatar else None,
                'followers': u.profile.followers_count,
            } for u in users
        ]
    })


# ============ ADMIN HELPERS ============
def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.profile.role == 'admin')


def is_moderator(user):
    return user.is_authenticated and (user.is_superuser or user.profile.role in ['moderator', 'admin'])


# ============ ADMIN DASHBOARD ============
@login_required
@user_passes_test(is_admin, login_url='/')
def admin_dashboard(request):
    total_users = User.objects.count()
    total_posts = Post.objects.count()
    total_comments = Comment.objects.count()
    total_messages = Message.objects.count()
    total_stories = Story.objects.count()

    week_ago = timezone.now() - timedelta(days=7)
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()
    new_posts_week = Post.objects.filter(created_at__gte=week_ago).count()

    top_users = User.objects.annotate(post_count=Count('posts')).order_by('-post_count')[:5]
    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_posts = Post.objects.select_related('author').order_by('-created_at')[:10]

    return render(request, 'social/admin_dashboard.html', {
        'total_users': total_users, 'total_posts': total_posts,
        'total_comments': total_comments, 'total_messages': total_messages,
        'total_stories': total_stories,
        'new_users_week': new_users_week, 'new_posts_week': new_posts_week,
        'top_users': top_users, 'recent_users': recent_users,
        'recent_posts': recent_posts,
        'unread_count': _unread(request.user),
    })


@login_required
@user_passes_test(is_admin, login_url='/')
def admin_users(request):
    query = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    users = User.objects.select_related('profile').order_by('-date_joined')
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query))
    if role_filter:
        users = users.filter(profile__role=role_filter)
    if status_filter == 'banned':
        users = users.filter(profile__is_banned=True)
    elif status_filter == 'active':
        users = users.filter(profile__is_banned=False)

    return render(request, 'social/admin_users.html', {
        'users': users, 'query': query,
        'role_filter': role_filter, 'status_filter': status_filter,
        'unread_count': _unread(request.user),
    })


@login_required
@user_passes_test(is_admin, login_url='/')
@require_POST
def admin_change_role(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target == request.user or target.is_superuser:
        return JsonResponse({'error': 'Not allowed'}, status=400)

    new_role = request.POST.get('role', 'user')
    if new_role not in ['user', 'moderator', 'admin']:
        return JsonResponse({'error': 'Invalid role'}, status=400)

    target.profile.role = new_role
    target.profile.save()
    target.is_staff = (new_role == 'admin')
    target.save()
    return JsonResponse({'success': True, 'role': new_role})


@login_required
@user_passes_test(is_admin, login_url='/')
@require_POST
def admin_toggle_ban(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target == request.user or target.is_superuser:
        return JsonResponse({'error': 'Not allowed'}, status=400)

    target.profile.is_banned = not target.profile.is_banned
    if target.profile.is_banned:
        target.profile.ban_reason = request.POST.get('reason', '').strip()
    else:
        target.profile.ban_reason = ''
    target.profile.save()
    return JsonResponse({'success': True, 'banned': target.profile.is_banned})


@login_required
@user_passes_test(is_admin, login_url='/')
@require_POST
def admin_delete_user(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target == request.user or target.is_superuser:
        return JsonResponse({'error': 'Not allowed'}, status=400)
    username = target.username
    target.delete()
    return JsonResponse({'success': True, 'username': username})


@login_required
@user_passes_test(is_moderator, login_url='/')
def admin_posts(request):
    query = request.GET.get('q', '').strip()
    posts = Post.objects.select_related('author').order_by('-created_at')
    if query:
        posts = posts.filter(Q(content__icontains=query) | Q(author__username__icontains=query))
    return render(request, 'social/admin_posts.html', {
        'posts': posts[:100], 'query': query,
        'unread_count': _unread(request.user),
    })


@login_required
@user_passes_test(is_moderator, login_url='/')
@require_POST
def admin_delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.delete()
    return JsonResponse({'success': True})


@login_required
@user_passes_test(is_moderator, login_url='/')
def admin_comments(request):
    comments = Comment.objects.select_related('author', 'post__author').order_by('-created_at')[:200]
    return render(request, 'social/admin_comments.html', {
        'comments': comments,
        'unread_count': _unread(request.user),
    })


@login_required
@user_passes_test(is_moderator, login_url='/')
@require_POST
def admin_delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    comment.delete()
    return JsonResponse({'success': True})


@login_required
@user_passes_test(is_admin, login_url='/')
def admin_messages(request):
    msgs = Message.objects.select_related('sender', 'conversation').order_by('-created_at')[:100]
    return render(request, 'social/admin_messages.html', {
        'messages': msgs,
        'unread_count': _unread(request.user),
    })


@login_required
@user_passes_test(is_admin, login_url='/')
def admin_activity(request):
    recent_follows = Follow.objects.select_related('follower', 'following').order_by('-created_at')[:20]
    recent_likes = Like.objects.select_related('user', 'post__author').order_by('-created_at')[:20]
    recent_friends = Friendship.objects.select_related('user1', 'user2').order_by('-created_at')[:20]
    return render(request, 'social/admin_activity.html', {
        'recent_follows': recent_follows,
        'recent_likes': recent_likes,
        'recent_friends': recent_friends,
        'unread_count': _unread(request.user),
    })

# ============ POST SHARE ============
@login_required
@require_POST
def share_post(request, post_id):
    """Share a post to a friend via chat."""
    post = get_object_or_404(Post, id=post_id)
    recipient_id = request.POST.get('recipient_id')
    message = request.POST.get('message', '').strip()

    if not recipient_id:
        return JsonResponse({'error': 'Recipient required'}, status=400)

    recipient = get_object_or_404(User, id=recipient_id)

    # Check if blocked
    if Block.is_blocked(request.user, recipient):
        return JsonResponse({'error': 'Cannot share with this user'}, status=403)

    share = PostShare.objects.create(
        post=post, sender=request.user,
        recipient=recipient, message=message
    )

    Notification.objects.create(
        recipient=recipient, sender=request.user,
        notif_type='like', post=post
    )

    return JsonResponse({
        'status': 'ok',
        'shared_with': recipient.username,
    })


# ============ STORY REACTION ============
@login_required
@require_POST
def react_story(request, story_id):
    """React to a story with emoji."""
    story = get_object_or_404(Story, id=story_id)
    reaction = request.POST.get('reaction', 'love')

    if reaction not in ['love', 'haha', 'wow', 'sad', 'fire', 'clap']:
        return JsonResponse({'error': 'Invalid reaction'}, status=400)

    existing = StoryReaction.objects.filter(story=story, user=request.user).first()
    if existing:
        if existing.reaction == reaction:
            existing.delete()
            return JsonResponse({'removed': True, 'reaction': None})
        existing.reaction = reaction
        existing.save()
    else:
        StoryReaction.objects.create(story=story, user=request.user, reaction=reaction)

    if story.author != request.user:
        Notification.objects.create(
            recipient=story.author, sender=request.user,
            notif_type='like'
        )

    return JsonResponse({'status': 'ok', 'reaction': reaction})


# ============ BLOCK USER ============
@login_required
@require_POST
def toggle_block(request, username):
    """Block or unblock a user."""
    target = get_object_or_404(User, username=username)

    if target == request.user:
        return JsonResponse({'error': 'Cannot block yourself'}, status=400)

    existing = Block.objects.filter(blocker=request.user, blocked=target).first()
    if existing:
        existing.delete()
        return JsonResponse({'blocked': False, 'msg': f'Unblocked {target.username}'})

    Block.objects.create(blocker=request.user, blocked=target)

    # Remove friendship if exists
    Friendship.objects.filter(
        Q(user1=request.user, user2=target) | Q(user1=target, user2=request.user)
    ).delete()

    return JsonResponse({'blocked': True, 'msg': f'Blocked {target.username}'})


# ============ REPORT CONTENT ============
@login_required
@require_POST
def report_content(request):
    """Report a post or user."""
    post_id = request.POST.get('post_id')
    user_id = request.POST.get('user_id')
    reason = request.POST.get('reason', 'other')
    details = request.POST.get('details', '').strip()

    if reason not in ['spam', 'harassment', 'hate', 'violence', 'nudity', 'false_info', 'other']:
        return JsonResponse({'error': 'Invalid reason'}, status=400)

    report = Report.objects.create(
        reporter=request.user,
        post_id=post_id if post_id else None,
        reported_user_id=user_id if user_id else None,
        reason=reason,
        details=details
    )

    return JsonResponse({'status': 'ok', 'msg': 'Report submitted'})


# ============ HASHTAG EXPLORE ============
@login_required
def hashtag_explore(request, tag=None):
    """Explore trending hashtags or posts with a specific tag."""
    import re

    if tag:
        tag = tag.lower().lstrip('#')
        posts = Post.objects.filter(
            Q(content__icontains=f'#{tag}') & Q(privacy='public')
        ).select_related('author').order_by('-created_at')[:50]

        hashtag_obj, _ = Hashtag.objects.get_or_create(name=tag)

        return render(request, 'social/hashtag_posts.html', {
            'tag': tag,
            'posts': posts,
            'hashtag': hashtag_obj,
            'unread_count': _unread(request.user),
        })

    # Trending page
    trending = Hashtag.objects.order_by('-post_count')[:30]

    return render(request, 'social/explore.html', {
        'trending': trending,
        'unread_count': _unread(request.user),
    })


# ============ TRACK PROFILE VIEW ============
def track_profile_view(viewer, viewed):
    """Track when someone views a profile."""
    if viewer.is_authenticated and viewer != viewed:
        # Only create one view per day per viewer
        today = timezone.now().date()
        exists = ProfileView.objects.filter(
            viewer=viewer, viewed=viewed,
            created_at__date=today
        ).exists()
        if not exists:
            ProfileView.objects.create(viewer=viewer, viewed=viewed)


@login_required
def profile_viewers(request):
    """Who viewed my profile."""
    viewers = ProfileView.objects.filter(
        viewed=request.user
    ).select_related('viewer').order_by('-created_at')[:50]

    # Unique viewers
    seen = set()
    unique_viewers = []
    for v in viewers:
        if v.viewer_id not in seen:
            seen.add(v.viewer_id)
            unique_viewers.append(v)

    return render(request, 'social/profile_viewers.html', {
        'viewers': unique_viewers,
        'total': len(unique_viewers),
        'unread_count': _unread(request.user),
    })
from django.core.management import call_command
from django.http import HttpResponse

def run_migrations(request):
    """Temporary view to run migrations on Render."""
    try:
        call_command('migrate', interactive=False)
        call_command('collectstatic', interactive=False)
        call_command('autocreate_superuser')
        return HttpResponse("✅ Migrations + superuser created!")
    except Exception as e:
        return HttpResponse(f"❌ Error: {str(e)}")

# ============ COLLECTIONS ============
@login_required
def collections_list(request):
    """Show all collections of current user."""
    collections = request.user.collections.all()

    return render(request, 'social/collections.html', {
        'collections': collections,
        'unread_count': _unread(request.user),
    })


@login_required
def collection_detail(request, collection_id):
    """Show posts inside a collection."""
    collection = get_object_or_404(Collection, id=collection_id)

    # Privacy check
    if collection.user != request.user and not collection.is_public:
        return redirect('collections_list')

    items = collection.items.select_related('post__author').all()

    return render(request, 'social/collection_detail.html', {
        'collection': collection,
        'items': items,
        'unread_count': _unread(request.user),
    })


@login_required
@require_POST
def create_collection(request):
    """Create a new collection."""
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    is_public = request.POST.get('is_public', 'false') == 'true'

    if not name:
        return JsonResponse({'error': 'Name required'}, status=400)

    if Collection.objects.filter(user=request.user, name=name).exists():
        return JsonResponse({'error': 'Collection already exists'}, status=400)

    collection = Collection.objects.create(
        user=request.user,
        name=name,
        description=description,
        is_public=is_public
    )

    return JsonResponse({
        'status': 'ok',
        'id': collection.id,
        'name': collection.name,
        'description': collection.description,
        'is_public': collection.is_public,
    })


@login_required
@require_POST
def delete_collection(request, collection_id):
    """Delete a collection."""
    collection = get_object_or_404(Collection, id=collection_id, user=request.user)
    collection.delete()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def add_to_collection(request, post_id):
    """Add post to a collection."""
    post = get_object_or_404(Post, id=post_id)
    collection_id = request.POST.get('collection_id')

    if not collection_id:
        return JsonResponse({'error': 'Collection required'}, status=400)

    collection = get_object_or_404(Collection, id=collection_id, user=request.user)

    item, created = CollectionItem.objects.get_or_create(
        collection=collection, post=post
    )

    if created:
        return JsonResponse({'status': 'ok', 'msg': f'Added to {collection.name}'})
    else:
        return JsonResponse({'status': 'exists', 'msg': 'Already in collection'})


@login_required
@require_POST
def remove_from_collection(request, item_id):
    """Remove post from collection."""
    item = get_object_or_404(CollectionItem, id=item_id, collection__user=request.user)
    item.delete()
    return JsonResponse({'status': 'ok'})


@login_required
def user_collections(request):
    """API: Get user's collections for dropdown."""
    collections = request.user.collections.all()

    return JsonResponse({
        'collections': [
            {
                'id': c.id,
                'name': c.name,
                'post_count': c.post_count,
            } for c in collections
        ]
    })