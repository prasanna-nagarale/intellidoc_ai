# intellidoc/core/context_processors.py
from django.conf import settings

class UserWrapper:
    """
    Wrap request.user to provide safe attributes used in templates:
      - subscription_plan
      - daily_query_count
      - get_daily_limit() -> returns int
    If underlying user has a profile or attributes, use them; otherwise return safe defaults.
    """
    def __init__(self, user):
        self._user = user

    def __getattr__(self, name):
        # fallback to underlying user attributes (email, is_authenticated, etc.)
        return getattr(self._user, name)

    @property
    def subscription_plan(self):
        # try common profile names
        profile = getattr(self._user, 'profile', None) or getattr(self._user, 'userprofile', None)
        if profile:
            return getattr(profile, 'subscription_plan', 'free')
        return 'free'

    @property
    def daily_query_count(self):
        profile = getattr(self._user, 'profile', None) or getattr(self._user, 'userprofile', None)
        if profile:
            return getattr(profile, 'daily_query_count', 0)
        return 0

    def get_daily_limit(self):
        profile = getattr(self._user, 'profile', None) or getattr(self._user, 'userprofile', None)
        if profile:
            limit = getattr(profile, 'get_daily_limit', None)
            if callable(limit):
                return limit()
            return getattr(profile, 'daily_limit', 20)
        return 20


def user_context(request):
    """
    Inject a wrapped 'user' into template context so existing templates that call:
      user.subscription_plan, user.daily_query_count, user.get_daily_limit()
    will work without requiring a custom user model.
    Note: this intentionally returns 'user' to shadow the default user context processor (we'll append it last).
    """
    try:
        return {'user': UserWrapper(request.user)}
    except Exception:
        # fallback: safe defaults
        return {'user': UserWrapper(request.user)}
