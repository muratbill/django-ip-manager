from __future__ import annotations

from typing import Optional
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
import ipaddress
from .models import IPAddressAllocation, Subnet
from .netprobe import ip_in_use


def _probe_iface() -> str:
    return getattr(settings, "IPAM_PROBE_IFACE", "wlo1")


def _probe_timeout() -> float:
    return float(getattr(settings, "IPAM_PROBE_TIMEOUT", 1.0))


def _candidate_ips(subnet: Subnet):
    for ip_obj in subnet.network.hosts():
        ip = str(ip_obj)
        if ip in subnet.excluded_set:
            continue
        yield ip


def _ip_is_used_in_db(subnet: Subnet, ip: str) -> bool:
    return IPAddressAllocation.objects.filter(
        subnet=subnet,
        ip=ip,
        status=IPAddressAllocation.Status.USED,
    ).exists()


def _claim_ip_row(subnet: Subnet, ip: str, user, hostname: str, description: str) -> Optional[IPAddressAllocation]:
    """
    Claim an IP by REUSING the existing row (because subnet+ip is unique).
    """
    # already used by someone in DB?
    if _ip_is_used_in_db(subnet, ip):
        return None

    # LAN gate
    iface = _probe_iface()
    timeout = _probe_timeout()
    if ip_in_use(ip, iface=iface, timeout=timeout):
        return None

    # row exists? reuse it
    row = IPAddressAllocation.objects.filter(subnet=subnet, ip=ip).first()
    if row:
        if row.status != IPAddressAllocation.Status.RELEASED:
            return None

        row.status = IPAddressAllocation.Status.USED
        row.owner = user
        row.hostname = hostname
        row.description = description
        row.claimed_at = timezone.now()
        row.released_at = None
        row.released_by = None
        row.save(update_fields=[
            "status", "owner", "hostname", "description",
            "claimed_at", "released_at", "released_by"
        ])
        return row

    # if no row exists at all, create it
    try:
        return IPAddressAllocation.objects.create(
            subnet=subnet,
            ip=ip,
            status=IPAddressAllocation.Status.USED,
            owner=user,
            hostname=hostname,
            description=description,
            claimed_at=timezone.now(),
        )
    except IntegrityError:
        return None


def claim_first_free_ip(*, subnet_id: int, user, hostname: str = "", description: str = "") -> Optional[IPAddressAllocation]:
    for _ in range(5):
        with transaction.atomic():
            subnet = Subnet.objects.select_for_update().get(id=subnet_id, is_active=True)

            for ip in _candidate_ips(subnet):
                alloc = _claim_ip_row(subnet, ip, user, hostname, description)
                if alloc:
                    return alloc
    return None


def claim_specific_ip(*, subnet_id: int, ip: str, user, hostname: str = "", description: str = "") -> Optional[IPAddressAllocation]:
    ip = ip.strip()

    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return None

    for _ in range(3):
        with transaction.atomic():
            subnet = Subnet.objects.select_for_update().get(id=subnet_id, is_active=True)

            # must be IPv4 inside subnet
            if ip_obj.version != 4:
                return None
            if ip_obj not in subnet.network:
                return None

            # exclude special addresses + excluded list
            if ip in subnet.excluded_set:
                return None
            if ip_obj == subnet.network.network_address or ip_obj == subnet.network.broadcast_address:
                return None

            # already USED in DB?
            if IPAddressAllocation.objects.filter(
                subnet=subnet, ip=ip, status=IPAddressAllocation.Status.USED
            ).exists():
                return None

            # LAN gate
            if ip_in_use(ip, iface=_probe_iface(), timeout=_probe_timeout()):
                return None

            # reuse RELEASED row if exists (because unique constraint)
            row = IPAddressAllocation.objects.filter(subnet=subnet, ip=ip).first()
            if row:
                if row.status != IPAddressAllocation.Status.RELEASED:
                    return None
                row.status = IPAddressAllocation.Status.USED
                row.owner = user
                row.hostname = hostname
                row.description = description
                row.claimed_at = timezone.now()
                row.released_at = None
                row.released_by = None
                row.save(update_fields=[
                    "status","owner","hostname","description",
                    "claimed_at","released_at","released_by"
                ])
                return row

            # create new row
            return IPAddressAllocation.objects.create(
                subnet=subnet,
                ip=ip,
                status=IPAddressAllocation.Status.USED,
                owner=user,
                hostname=hostname,
                description=description,
                claimed_at=timezone.now(),
            )

    return None

def find_free_ip(subnet: Subnet) -> Optional[str]:
    iface = _probe_iface()
    timeout = _probe_timeout()

    for ip in _candidate_ips(subnet):
        # not USED in DB?
        if IPAddressAllocation.objects.filter(subnet=subnet, ip=ip, status=IPAddressAllocation.Status.USED).exists():
            continue
        # LAN gate
        if ip_in_use(ip, iface=iface, timeout=timeout):
            continue
        return ip
    return None


def release_allocation(allocation, released_by=None):
    allocation.status = allocation.Status.RELEASED
    allocation.released_at = timezone.now()
    allocation.released_by = released_by
    allocation.save(update_fields=["status", "released_at", "released_by"])
    return allocation
