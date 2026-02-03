import subprocess
import re
def seen_in_neigh(ip: str, iface: str) -> bool:
    """
    True if kernel neighbor table has an lladdr for this IP on iface.
    This is very reliable on same L2 and works even when arping fails on Wi-Fi.
    """
    res = subprocess.run(
        ["ip", "neigh", "show", ip, "dev", iface],
        capture_output=True,
        text=True,
    )
    out = (res.stdout or "").strip()
    # Example: "192.168.1.6 lladdr 42:c6:3c:7a:65:bc STALE"
    return ("lladdr" in out)

def ping_alive(ip: str, timeout: float = 1.0) -> bool:
    """
    True if ping returns success.
    -c 1 one packet, -W timeout seconds
    """
    res = subprocess.run(
        ["ping", "-c", "1", "-W", str(int(max(1, timeout))), ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return res.returncode == 0

def ip_in_use(ip: str, iface: str, timeout: float = 1.0) -> bool:
    """
    Conservative: treat as in-use if either:
    - neigh table already has a MAC, OR
    - ping replies
    """
    if seen_in_neigh(ip, iface):
        return True
    return ping_alive(ip, timeout=timeout)
