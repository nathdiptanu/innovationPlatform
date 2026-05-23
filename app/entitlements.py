from functools import wraps

from flask import abort, g, redirect, request, session, url_for
from bson import ObjectId

from .access_config import PUBLIC_SCREENS, USER_SCREEN_ACCESS
from .db import collection


def load_current_user():
    user_id = session.get("user_id")
    g.user = collection("users").find_one({"_id": ObjectId(user_id), "active": True}) if user_id else None
    return g.user


def user_role(user=None):
    user = user or getattr(g, "user", None)
    return user["role"] if user else "anonymous"


def can_access(screen, user=None):
    if screen in PUBLIC_SCREENS:
        return True
    user = user or getattr(g, "user", None)
    if not user:
        return False
    configured = USER_SCREEN_ACCESS.get(user["username"], set())
    if screen in configured:
        return True
    if screen == "core":
        return user.get("role") == "core"
    if screen == "jury":
        return user.get("role") in {"jury", "jury_lead"}
    return False


def home_for_user(user):
    if can_access("core", user):
        return url_for("core.dashboard")
    if can_access("jury", user):
        return url_for("jury.dashboard")
    return url_for("public.home")


def require_screen(screen):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = getattr(g, "user", None) or load_current_user()
            if not user and screen != "public":
                return redirect(url_for("auth.login", next=request.full_path))
            if not can_access(screen, user):
                abort(403, f"{screen.title()} access is not granted for this account.")
            return view(*args, **kwargs)

        return wrapped

    return decorator


def is_assigned_to_category(user, category, lead_only=False):
    if not user or not can_access("jury", user):
        return False
    juror_id = str(user["_id"])
    if lead_only:
        return juror_id in category.get("jury_lead_ids", [])
    return juror_id in category.get("jury_member_ids", []) or juror_id in category.get("jury_lead_ids", [])


def require_category_assignment(category, lead_only=False):
    user = getattr(g, "user", None) or load_current_user()
    if not is_assigned_to_category(user, category, lead_only):
        abort(403, "This category is outside your jury assignment.")


def is_idea_contributor(user, idea):
    username = (user or {}).get("username", "").strip().lower()
    contributor_names = {
        contributor.get("username", "").strip().lower()
        for contributor in idea.get("contributors", [])
        if contributor.get("username")
    }
    return bool(username and username in contributor_names)
