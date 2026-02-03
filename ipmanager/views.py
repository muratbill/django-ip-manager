from datetime import timedelta
import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from .forms import ClaimForm
from .models import IPAddressAllocation, Subnet
from .services import claim_first_free_ip, claim_specific_ip,release_allocation, find_free_ip


@login_required
def subnet_list(request):
    subnets = Subnet.objects.filter(is_active=True).order_by("name")

    rows = []
    for s in subnets:
        used_count = IPAddressAllocation.objects.filter(
            subnet=s, status=IPAddressAllocation.Status.USED
        ).count()

        # /23-/24 is small: OK to compute in memory
        candidates = [str(ip) for ip in s.network.hosts() if str(ip) not in s.excluded_set]
        usable_count = len(candidates)
        free_count = max(usable_count - used_count, 0)

        first_ip, last_ip = s.usable_range()

        rows.append({
            "subnet": s,
            "used_count": used_count,
            "free_count": free_count,
            "usable_count": usable_count,
            "first_ip": first_ip,
            "last_ip": last_ip,
        })

    return render(request, "ipmanager/subnet_list.html", {"rows": rows})


@login_required
def subnet_detail(request, subnet_id: int):
    subnet = get_object_or_404(Subnet, id=subnet_id, is_active=True)

    # filters
    q = (request.GET.get("q") or "").strip()
    mine = request.GET.get("mine") == "1"
    used_only = request.GET.get("used") == "1"
    stale_only = request.GET.get("stale") == "1"

    stale_days = 30
    stale_cutoff = timezone.now() - timedelta(days=stale_days)

    first_ip, last_ip = subnet.usable_range()

    allocations = IPAddressAllocation.objects.filter(subnet=subnet).select_related("owner")

    if q:
        allocations = allocations.filter(
            Q(ip__icontains=q) |
            Q(owner__username__icontains=q) |
            Q(hostname__icontains=q) |
            Q(description__icontains=q)
        )

    if mine:
        allocations = allocations.filter(owner=request.user)

    if used_only:
        allocations = allocations.filter(status=IPAddressAllocation.Status.USED)

    if stale_only:
        allocations = allocations.filter(
            status=IPAddressAllocation.Status.USED,
            claimed_at__lte=stale_cutoff
        )

    allocations = allocations.order_by("-claimed_at")

    # stale list for admin section + banner count
    stale_allocations = IPAddressAllocation.objects.filter(
        subnet=subnet,
        status=IPAddressAllocation.Status.USED,
        claimed_at__lte=stale_cutoff
    ).select_related("owner").order_by("claimed_at")

    stale_count = stale_allocations.count()

    # Free-IP check (IMPORTANT: find_free_ip must include ip_in_use() gate)
    free_ip = None
    if request.GET.get("check_free") == "1":
        free_ip = find_free_ip(subnet)

    form = ClaimForm()

    return render(
        request,
        "ipmanager/subnet_detail.html",
        {
            "subnet": subnet,
            "first_ip": first_ip,
            "last_ip": last_ip,
            "allocations": allocations,
            "q": q,
            "mine": mine,
            "used_only": used_only,
            "stale_only": stale_only,
            "stale_days": stale_days,
            "stale_cutoff": stale_cutoff,
            "stale_count": stale_count,
            "stale_allocations": stale_allocations,
            "free_ip": free_ip,
            "form": form,
        },
    )


@login_required
@require_POST
def claim_ip(request, subnet_id: int):
    subnet = get_object_or_404(Subnet, id=subnet_id, is_active=True)
    form = ClaimForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Please fix the form errors.")
        return redirect("subnet_detail", subnet_id=subnet.id)

    requested_ip = (form.cleaned_data.get("requested_ip") or "").strip()
    hostname = (form.cleaned_data.get("hostname") or "").strip()
    description = (form.cleaned_data.get("description") or "").strip()

    if requested_ip:
        alloc = claim_specific_ip(
            subnet_id=subnet.id,
            ip=requested_ip,
            user=request.user,
            hostname=hostname,
            description=description,
        )
        if alloc:
            messages.success(request, f"Claimed {alloc.ip}.")
        else:
            messages.error(request, f"Could not claim {requested_ip}. It may be in use, excluded, outside subnet, or already claimed.")
    else:
        alloc = claim_first_free_ip(
            subnet_id=subnet.id,
            user=request.user,
            hostname=hostname,
            description=description,
        )
        if alloc:
            messages.success(request, f"Claimed {alloc.ip}.")
        else:
            messages.error(request, "No free IP available (or all candidates look in-use on the network).")

    return redirect("subnet_detail", subnet_id=subnet.id)

@login_required
@require_POST
def release_ip(request, allocation_id: int):
    allocation = get_object_or_404(IPAddressAllocation, id=allocation_id)

    # server-side authorization (IMPORTANT)
    if not (request.user.is_staff or request.user.id == allocation.owner_id):
        raise PermissionDenied

    release_allocation(allocation, released_by=request.user)
    return redirect("subnet_detail", subnet_id=allocation.subnet_id)


@login_required
def stale_csv(request, subnet_id: int):
    if not request.user.is_staff:
        return HttpResponse("Forbidden", status=403)

    subnet = get_object_or_404(Subnet, id=subnet_id, is_active=True)

    stale_days = 30
    stale_cutoff = timezone.now() - timedelta(days=stale_days)

    qs = IPAddressAllocation.objects.filter(
        subnet=subnet,
        status=IPAddressAllocation.Status.USED,
        claimed_at__lte=stale_cutoff
    ).select_related("owner").order_by("claimed_at")

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="stale_{subnet.name}_{stale_days}d.csv"'

    w = csv.writer(resp)
    w.writerow(["subnet", "cidr", "ip", "owner", "hostname", "claimed_at", "age_days", "description"])
    now = timezone.now()

    for a in qs:
        age_days = (now - a.claimed_at).days
        w.writerow([
            subnet.name,
            subnet.cidr,
            a.ip,
            a.owner.username,
            a.hostname,
            a.claimed_at.isoformat(timespec="seconds"),
            age_days,
            (a.description or "").replace("\n", " ").strip(),
        ])

    return resp

