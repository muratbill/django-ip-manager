from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

class ForcePasswordChangeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        profile = getattr(request.user, "userprofile", None)
        if not profile or not profile.must_change_password:
            return None

        # allow only these endpoints while forced
        allowed_paths = {
            reverse("password_change"),
            reverse("password_change_done"),
            reverse("logout"),
        }

        if request.path in allowed_paths:
            return None

        # IMPORTANT: even if user tries /admin/, force them to /accounts/password_change/
        return redirect("password_change")