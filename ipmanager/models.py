from django.db import models
import ipaddress
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
class Subnet(models.Model):
    name = models.CharField(max_length=100, unique=True)
    cidr = models.CharField(max_length=18)  # IPv4 CIDR e.g. 10.10.1.0/24
    gateway = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # optional: additional exclusions per subnet (comma-separated)
    excluded_ips = models.TextField(blank=True, help_text="Comma-separated IPv4 addresses to exclude")

    def clean(self):
        try:
            net = ipaddress.ip_network(self.cidr, strict=False)
        except ValueError as e:
            raise ValidationError({"cidr": str(e)})

        if net.version != 4:
            raise ValidationError({"cidr": "Only IPv4 is supported."})

        if self.gateway:
            gw = ipaddress.ip_address(self.gateway)
            if gw not in net:
                raise ValidationError({"gateway": "Gateway must be inside the subnet CIDR."})

    @property
    def network(self):
        return ipaddress.ip_network(self.cidr, strict=False)

    @property
    def excluded_set(self) -> set[str]:
        out = set()
        if self.gateway:
            out.add(str(self.gateway))
        if self.excluded_ips:
            for item in self.excluded_ips.split(","):
                item = item.strip()
                if item:
                    out.add(item)
        return out

    def usable_range(self) -> tuple[str | None, str | None]:
        # hosts() excludes network/broadcast automatically for IPv4
        candidates = [str(ip) for ip in self.network.hosts() if str(ip) not in self.excluded_set]
        if not candidates:
            return (None, None)
        return (candidates[0], candidates[-1])

    def __str__(self):
        return f"{self.name} ({self.cidr})"


class IPAddressAllocation(models.Model):
    class Status(models.TextChoices):
        USED = "USED"
        RELEASED = "RELEASED"

    subnet = models.ForeignKey(Subnet, on_delete=models.PROTECT, related_name="allocations")
    ip = models.GenericIPAddressField(protocol="IPv4")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.USED)

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ip_allocations")
    hostname = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    claimed_at = models.DateTimeField(default=timezone.now)
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="released_allocations",
    )   

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["subnet", "ip"], name="uniq_ip_per_subnet"),
        ]
        indexes = [
            models.Index(fields=["subnet", "status"]),
            models.Index(fields=["owner", "status"]),
        ]

    def __str__(self):
        return f"{self.ip} ({self.status})"

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    must_change_password = models.BooleanField(default=True)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, must_change_password=True)

