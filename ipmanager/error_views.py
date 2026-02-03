from django.shortcuts import render

def forbidden_view(request, exception=None):
    # Django will use templates/403.html
    return render(request, "403.html", status=403)

