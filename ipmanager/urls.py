from django.urls import include, path
from . import views

urlpatterns = [
    path("", views.subnet_list, name="subnet_list"),
    path("subnets/<int:subnet_id>/", views.subnet_detail, name="subnet_detail"),
    path("subnets/<int:subnet_id>/claim/", views.claim_ip, name="claim_ip"),
    path("allocations/<int:allocation_id>/release/", views.release_ip, name="release_ip"),
     path("subnets/<int:subnet_id>/stale.csv", views.stale_csv, name="stale_csv"),
]
