from django.contrib import admin
from .models import IPAddressAllocation, Subnet

@admin.register(Subnet)
class SubnetAdmin(admin.ModelAdmin):
    list_display = ("name", "cidr", "gateway", "is_active")
    search_fields = ("name", "cidr", "gateway")
    list_filter = ("is_active",)

@admin.register(IPAddressAllocation)
class IPAllocationAdmin(admin.ModelAdmin):
    list_display = ("ip", "subnet", "status", "owner", "hostname", "claimed_at", "released_at")
    search_fields = ("ip", "hostname", "owner__username", "subnet__name")
    list_filter = ("status", "subnet")


admin.site.site_header = "IP Manager"
admin.site.site_title = "IP Manager Admin"
admin.site.index_title = "Administration"

