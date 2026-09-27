# social/middleware.py
from django.utils import timezone
from datetime import timedelta


class LastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # ✅ Safe update — only for logged-in users with a profile
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                # Throttle: only update every 60 seconds
                now = timezone.now()
                if not profile.last_seen or (now - profile.last_seen) > timedelta(seconds=60):
                    profile.last_seen = now
                    profile.save(update_fields=['last_seen'])
            except Exception:
                # Profile missing or column missing — skip silently
                pass

        return response