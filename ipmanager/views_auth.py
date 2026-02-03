from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

class ForcePasswordChangeView(PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("password_change_done")

    def form_valid(self, form):
        resp = super().form_valid(form)

        profile = getattr(self.request.user, "userprofile", None)
        if profile:
            profile.must_change_password = False
            profile.save(update_fields=["must_change_password"])

        return resp
