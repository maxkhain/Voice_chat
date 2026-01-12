"""
Local network scanning module.

Discovers available PCs on the local network and retrieves their IP addresses and hostnames.
Uses ARP scanning (primary) + ICMP ping (fallback) for reliable detection.
ARP is more reliable than ping as it works even when devices have firewall blocking ICMP.
"""
import socket
import subprocess
import threading
import ipaddress
from typing import List, Dict, Tuple
import time
import platform
import re


def get_local_ip():
    """
    Get the local machine's IP address.
    
    Returns:
        str: Local IP address
    """
    try:
        # Create a socket connection to determine local IP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def get_network_range():
    """
    Get the local network CIDR range.
    
    Returns:
        str: Network range (e.g., "192.168.1.0/24")
    """
    local_ip = get_local_ip()
    # Assume /24 network (common for home/office networks)
    parts = local_ip.split('.')
    network = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return network


def resolve_hostname(ip_address: str) -> str:
    """
    Resolve hostname from IP address.
    
    Args:
        ip_address: IP address to resolve
        
    Returns:
        str: Hostname or IP if resolution fails
    """
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        # Return just the hostname without domain
        return hostname.split('.')[0]
    except Exception:
        return ip_address


def get_arp_table() -> List[Dict]:
    """
    Get ARP table entries for local network devices.
    Much faster and more reliable than ping (works even with firewall blocking ICMP).
    
    Returns:
        List[Dict]: List of dicts with 'ip' and 'mac' keys for each ARP entry
    """
    arp_devices = []
    
    try:
        if platform.system() == "Windows":
            # Windows: use arp -a command
            output = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
            # Parse output: lines like "192.168.1.5       00-1a-2b-3c-4d-5e     dynamic"
            for line in output.stdout.split('\n'):
                if '.' in line:  # Contains IP
                    parts = line.split()
                    if len(parts) >= 1:
                        try:
                            ip = parts[0].strip()
                            if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
                                arp_devices.append({'ip': ip})
                        except Exception:
                            pass
        else:
            # Unix/Linux: use ip neigh or arp command
            try:
                output = subprocess.run(["ip", "neigh"], capture_output=True, text=True, timeout=5)
                # Parse output: "192.168.1.5 dev eth0 lladdr 00:1a:2b:3c:4d:5e REACHABLE"
                for line in output.stdout.split('\n'):
                    if '.' in line:
                        parts = line.split()
                        if len(parts) >= 1:
                            try:
                                ip = parts[0].strip()
                                if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
                                    arp_devices.append({'ip': ip})
                            except Exception:
                                pass
            except Exception:
                # Fallback to arp command
                output = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
                for line in output.stdout.split('\n'):
                    if '.' in line:
                        parts = line.split()
                        if len(parts) >= 1:
                            try:
                                ip = parts[1].strip('()')
                                if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
                                    arp_devices.append({'ip': ip})
                            except Exception:
                                pass
    except Exception as e:
        print(f"[WARNING] ARP scan failed: {e}")
    
    # Remove duplicates
    seen = set()
    unique_devices = []
    for device in arp_devices:
        if device['ip'] not in seen:
            seen.add(device['ip'])
            unique_devices.append(device)
    
    return unique_devices


def ping_host_windows(ip_address: str, timeout: float = 0.5) -> bool:
    """
    Ping a host on Windows using ICMP.
    
    Args:
        ip_address: IP to ping
        timeout: Timeout in seconds
        
    Returns:
        bool: True if host is reachable
    """
    try:
        output = subprocess.run(
            ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip_address],
            capture_output=True,
            timeout=timeout + 0.5
        )
        return output.returncode == 0
    except Exception:
        return False


def ping_host_unix(ip_address: str, timeout: float = 0.5) -> bool:
    """
    Ping a host on Unix/Linux using ICMP.
    
    Args:
        ip_address: IP to ping
        timeout: Timeout in seconds
        
    Returns:
        bool: True if host is reachable
    """
    try:
        output = subprocess.run(
            ["ping", "-c", "1", "-W", str(int(timeout * 1000)), ip_address],
            capture_output=True,
            timeout=timeout + 0.5
        )
        return output.returncode == 0
    except Exception:
        return False


def ping_host(ip_address: str, timeout: float = 0.5) -> bool:
    """
    Ping a host (cross-platform).
    
    Args:
        ip_address: IP to ping
        timeout: Timeout in seconds
        
    Returns:
        bool: True if host is reachable
    """
    import platform
    if platform.system() == "Windows":
        return ping_host_windows(ip_address, timeout)
    else:
        return ping_host_unix(ip_address, timeout)


def scan_network_threaded(
    network_range: str = None,
    timeout: float = 0.5,
    max_threads: int = 30,
    progress_callback=None
) -> List[Dict]:
    """
    Scan local network for active hosts using multi-threaded ping.
    
    Args:
        network_range: Network to scan (e.g., "192.168.1.0/24"), defaults to local network
        timeout: Ping timeout in seconds (default 0.5 for speed)
        max_threads: Number of concurrent threads (default 30)
        progress_callback: Optional callback(current, total) for progress updates
        
    Returns:
        List[Dict]: List of dicts with 'ip' and 'hostname' keys
    """
    if network_range is None:
        network_range = get_network_range()
    
    results = []
    results_lock = threading.Lock()
    active_count = [0]  # Use list to allow modification in nested function
    
    try:
        network = ipaddress.ip_network(network_range, strict=False)
    except Exception as e:
        print(f"[ERROR] Invalid network range: {e}")
        return results
    
    all_ips = [str(ip) for ip in network.hosts()]
    total = len(all_ips)
    
    def ping_and_resolve(ip):
        """Ping IP and resolve hostname if reachable."""
        try:
            if ping_host(ip, timeout):
                # Only resolve hostname if needed (can be slow)
                hostname = resolve_hostname(ip)
                with results_lock:
                    results.append({'ip': ip, 'hostname': hostname})
                    if progress_callback:
                        progress_callback(len(results), total)
        finally:
            with results_lock:
                active_count[0] -= 1
    
    # Queue-based threading for better control
    thread_queue = list(all_ips)
    all_threads = []
    
    # Start initial batch of threads
    for _ in range(min(max_threads, len(thread_queue))):
        if thread_queue:
            ip = thread_queue.pop(0)
            active_count[0] += 1
            t = threading.Thread(target=ping_and_resolve, args=(ip,), daemon=True)
            t.start()
            all_threads.append(t)
    
    # Keep feeding threads as they complete
    while thread_queue or active_count[0] > 0:
        # Start new threads if queue has items
        while len([t for t in all_threads if t.is_alive()]) < max_threads and thread_queue:
            ip = thread_queue.pop(0)
            active_count[0] += 1
            t = threading.Thread(target=ping_and_resolve, args=(ip,), daemon=True)
            t.start()
            all_threads.append(t)
        
        # Small sleep to avoid busy waiting
        time.sleep(0.01)
    
    # Wait for remaining threads
    for t in all_threads:
        t.join(timeout=timeout + 1)
    
    # Sort by IP address
    results.sort(key=lambda x: tuple(map(int, x['ip'].split('.'))))
    
    return results


def scan_network(
    network_range: str = None,
    timeout: float = 0.5,
    progress_callback=None,
    use_arp: bool = True
) -> List[Dict]:
    """
    Scan local network for active hosts (optimized with ARP support).
    
    Uses ARP first (faster, more reliable) then falls back to ICMP ping.
    
    Args:
        network_range: Network to scan (e.g., "192.168.1.0/24"), defaults to local network
        timeout: Ping timeout in seconds (default 0.5 for speed)
        progress_callback: Optional callback(current, total) for progress updates
        use_arp: Use ARP scan first (recommended, catches devices blocking ICMP)
        
    Returns:
        List[Dict]: List of dicts with 'ip' and 'hostname' keys
    """
    results = []
    
    # Try ARP scan first (faster and more reliable)
    if use_arp:
        arp_devices = get_arp_table()
        print(f"[OK] ARP scan found {len(arp_devices)} devices")
        
        # Resolve hostnames for ARP devices
        for device in arp_devices:
            hostname = resolve_hostname(device['ip'])
            results.append({'ip': device['ip'], 'hostname': hostname})
    
    # Then use ICMP ping to find any additional devices
    if network_range is None:
        network_range = get_network_range()
    
    # Only ping if we didn't find much via ARP, or to supplement
    if len(results) < 5:  # If ARP found few devices, try ping
        print(f"[INFO] Supplementing with ICMP ping scan...")
        ping_results = scan_network_threaded(network_range, timeout, max_threads=30, progress_callback=progress_callback)
        
        # Add ping results that aren't already in ARP results
        arp_ips = {r['ip'] for r in results}
        for device in ping_results:
            if device['ip'] not in arp_ips:
                results.append(device)
    
    # Remove duplicates and sort
    unique_results = {}
    for device in results:
        if device['ip'] not in unique_results:
            unique_results[device['ip']] = device
    
    results = list(unique_results.values())
    results.sort(key=lambda x: tuple(map(int, x['ip'].split('.'))))
    
    return results


def scan_network_async(callback, network_range=None, timeout=0.5, use_arp=True):
    """
    Scan network asynchronously in background thread (optimized with ARP).
    
    Args:
        callback: Function to call with results list when scan completes
        network_range: Network to scan
        timeout: Ping timeout (default 0.5 seconds for speed)
        use_arp: Use ARP scan first (recommended, catches devices blocking ICMP)
    """
    def scan_thread():
        results = scan_network(network_range, timeout, use_arp=use_arp)
        callback(results)
    
    t = threading.Thread(target=scan_thread, daemon=True)
    t.start()
    return t


def format_device_list(devices: List[Dict]) -> List[str]:
    """
    Format device list for display in UI.
    
    Args:
        devices: List of device dicts with 'ip' and 'hostname'
        
    Returns:
        List[str]: Formatted strings like "192.168.1.5 (Desktop-PC)"
    """
    return [f"{d['ip']} ({d['hostname']})" for d in devices]


def extract_ip_from_formatted(formatted_str: str) -> str:
    """
    Extract IP from formatted device string.
    
    Args:
        formatted_str: String like "192.168.1.5 (Desktop-PC)"
        
    Returns:
        str: IP address
    """
    return formatted_str.split(' ')[0]
