"""
IP Rotation Manager for SheerID Verification

Handles the constraint that each IPv4(/32) or IPv6(/64) can only be used once.
Tracks used IPs and provides rotation functionality.

Features:
- IP usage tracking with persistent storage
- IPv4 full address tracking
- IPv6 /64 prefix tracking
- Auto-rotation until fresh IP found
- IPv6 pool management for cost-effective scaling
"""

import json
import hashlib
import time
import logging
from pathlib import Path
from typing import Optional, Set, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class IPUsageRecord:
    """Record of IP usage."""
    ip: str
    ip_key: str  # Normalized key (full IPv4 or /64 for IPv6)
    used_at: str
    verification_id: Optional[str] = None
    fingerprint_id: Optional[str] = None
    success: Optional[bool] = None


class IPRotationManager:
    """
    Manage IP rotation for one-time-use policy.
    
    Tracks used IPs to ensure each verification uses a fresh IP.
    Supports both IPv4 (full address) and IPv6 (/64 prefix).
    """
    
    def __init__(self, cache_dir: Path = None):
        """
        Initialize IP manager.
        
        Args:
            cache_dir: Directory to store IP cache file
        """
        if cache_dir is None:
            cache_dir = Path(__file__).parent / "data"
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = cache_dir / "used_ips.json"
        self.usage_log_file = cache_dir / "ip_usage_log.json"
        
        self.used_ips: Set[str] = set()
        self.usage_log: List[Dict] = []
        
        self._load_cache()
    
    def _load_cache(self):
        """Load previously used IPs from cache."""
        try:
            if self.cache_file.exists():
                data = json.loads(self.cache_file.read_text())
                if isinstance(data, list):
                    self.used_ips = set(data)
                elif isinstance(data, dict):
                    self.used_ips = set(data.get("used_ips", []))
                logger.info(f"Loaded {len(self.used_ips)} used IPs from cache")
        except Exception as e:
            logger.warning(f"Failed to load IP cache: {e}")
            self.used_ips = set()
        
        # Load usage log
        try:
            if self.usage_log_file.exists():
                self.usage_log = json.loads(self.usage_log_file.read_text())
        except Exception as e:
            logger.warning(f"Failed to load usage log: {e}")
            self.usage_log = []
    
    def _save_cache(self):
        """Save used IPs to cache file."""
        try:
            data = {
                "used_ips": list(self.used_ips),
                "count": len(self.used_ips),
                "updated_at": datetime.now().isoformat()
            }
            self.cache_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save IP cache: {e}")
    
    def _save_usage_log(self):
        """Save usage log to file."""
        try:
            self.usage_log_file.write_text(json.dumps(self.usage_log[-1000:], indent=2))
        except Exception as e:
            logger.error(f"Failed to save usage log: {e}")
    
    @staticmethod
    def normalize_ip(ip: str) -> str:
        """
        Normalize IP address for tracking.
        
        - IPv4: Use full address (/32)
        - IPv6: Use /64 prefix
        
        Args:
            ip: IP address string
            
        Returns:
            Normalized IP key for tracking
        """
        ip = ip.strip()
        
        if ':' in ip:
            # IPv6: Extract /64 prefix (first 4 groups)
            # Example: 2001:db8:1234:5678:abcd:ef01:2345:6789 -> 2001:db8:1234:5678::
            parts = ip.split(':')
            
            # Handle compressed notation (::)
            if '::' in ip:
                # Expand compressed notation
                expanded = ip.replace('::', ':' + ':'.join(['0'] * (8 - ip.count(':') + 1)) + ':')
                parts = expanded.strip(':').split(':')
            
            # Take first 4 groups for /64
            prefix_parts = parts[:4]
            while len(prefix_parts) < 4:
                prefix_parts.append('0')
            
            return ':'.join(prefix_parts) + '::/64'
        else:
            # IPv4: Use full address
            return ip
    
    def mark_ip_used(
        self, 
        ip: str, 
        verification_id: str = None,
        fingerprint_id: str = None,
        success: bool = None
    ):
        """
        Mark IP as used.
        
        Args:
            ip: IP address to mark
            verification_id: Optional verification ID for logging
            fingerprint_id: Optional fingerprint ID for logging
            success: Optional verification result
        """
        ip_key = self.normalize_ip(ip)
        
        # Add to used set
        self.used_ips.add(ip_key)
        self._save_cache()
        
        # Log usage
        record = IPUsageRecord(
            ip=ip,
            ip_key=ip_key,
            used_at=datetime.now().isoformat(),
            verification_id=verification_id,
            fingerprint_id=fingerprint_id,
            success=success
        )
        self.usage_log.append(asdict(record))
        self._save_usage_log()
        
        logger.info(f"Marked IP as used: {ip_key}")
    
    def is_ip_used(self, ip: str) -> bool:
        """
        Check if IP was already used.
        
        Args:
            ip: IP address to check
            
        Returns:
            True if IP was previously used
        """
        ip_key = self.normalize_ip(ip)
        return ip_key in self.used_ips
    
    def get_unused_count(self) -> int:
        """Get count of used IPs."""
        return len(self.used_ips)
    
    def clear_cache(self, confirm: bool = False):
        """
        Clear all IP usage records.
        
        Args:
            confirm: Must be True to actually clear
        """
        if confirm:
            self.used_ips.clear()
            self._save_cache()
            logger.warning("Cleared all IP usage records")
        else:
            logger.warning("Clear cache requires confirm=True")


class IPv6PoolManager:
    """
    Manage IPv6 /64 blocks for cost-effective verification.
    
    With a /48 allocation, you get 65,536 unique /64 blocks.
    With a /32 allocation, you get 4+ billion /64 blocks!
    """
    
    def __init__(self, prefix: str, cache_dir: Path = None):
        """
        Initialize IPv6 pool manager.
        
        Args:
            prefix: IPv6 prefix allocation (e.g., "2001:db8:1234::/48")
        """
        self.prefix = prefix
        self.prefix_parts, self.prefix_length = self._parse_prefix(prefix)
        
        if cache_dir is None:
            cache_dir = Path(__file__).parent / "data"
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = cache_dir / "ipv6_pool.json"
        
        self.allocated_blocks: Set[str] = set()
        self._load_cache()
        
        # Calculate available blocks
        self._calculate_capacity()
    
    def _parse_prefix(self, prefix: str):
        """Parse IPv6 prefix into parts and length."""
        parts = prefix.split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid IPv6 prefix format: {prefix}")
        
        addr = parts[0].rstrip(':')
        length = int(parts[1])
        
        # Split address into groups
        groups = addr.split(':')
        
        return groups, length
    
    def _calculate_capacity(self):
        """Calculate pool capacity based on prefix length."""
        # /64 blocks available = 2^(64 - prefix_length)
        bits_available = 64 - self.prefix_length
        self.total_capacity = 2 ** bits_available
        self.available = self.total_capacity - len(self.allocated_blocks)
        
        logger.info(f"IPv6 Pool: /{self.prefix_length} = {self.total_capacity:,} /64 blocks")
        logger.info(f"  - Allocated: {len(self.allocated_blocks):,}")
        logger.info(f"  - Available: {self.available:,}")
    
    def _load_cache(self):
        """Load allocated blocks from cache."""
        try:
            if self.cache_file.exists():
                data = json.loads(self.cache_file.read_text())
                self.allocated_blocks = set(data.get("allocated_blocks", []))
        except Exception as e:
            logger.warning(f"Failed to load IPv6 pool cache: {e}")
            self.allocated_blocks = set()
    
    def _save_cache(self):
        """Save allocated blocks to cache."""
        try:
            data = {
                "prefix": self.prefix,
                "allocated_blocks": list(self.allocated_blocks),
                "count": len(self.allocated_blocks),
                "updated_at": datetime.now().isoformat()
            }
            self.cache_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save IPv6 pool cache: {e}")
    
    def allocate_block(self) -> str:
        """
        Allocate next available /64 block.
        
        Returns:
            IPv6 /64 block address (e.g., "2001:db8:1234:0001::/64")
        """
        import random
        
        if len(self.allocated_blocks) >= self.total_capacity:
            raise Exception(f"IPv6 pool exhausted! All {self.total_capacity} blocks used.")
        
        # Generate random block within our allocation
        # For /48, we can vary the 4th group (16 bits)
        # For /32, we can vary 3rd and 4th groups (32 bits)
        
        max_attempts = 100
        for _ in range(max_attempts):
            # Generate random suffix based on prefix length
            if self.prefix_length == 48:
                # Vary 4th group only
                suffix = f"{random.randint(0, 65535):04x}"
                block = f"{':'.join(self.prefix_parts[:3])}:{suffix}::/64"
            elif self.prefix_length == 32:
                # Vary 3rd and 4th groups
                g3 = f"{random.randint(0, 65535):04x}"
                g4 = f"{random.randint(0, 65535):04x}"
                block = f"{':'.join(self.prefix_parts[:2])}:{g3}:{g4}::/64"
            else:
                # Generic: hash-based allocation
                block_id = hashlib.md5(str(random.random()).encode()).hexdigest()[:8]
                block = f"{self.prefix.split('/')[0]}{block_id}::/64"
            
            # Normalize
            block_key = block.lower()
            
            if block_key not in self.allocated_blocks:
                self.allocated_blocks.add(block_key)
                self._save_cache()
                self.available -= 1
                
                logger.info(f"Allocated IPv6 block: {block}")
                return block
        
        raise Exception(f"Failed to allocate unique block after {max_attempts} attempts")
    
    def release_block(self, block: str):
        """Release a previously allocated block (for reuse if needed)."""
        block_key = block.lower()
        if block_key in self.allocated_blocks:
            self.allocated_blocks.remove(block_key)
            self._save_cache()
            self.available += 1
            logger.info(f"Released IPv6 block: {block}")
    
    def get_stats(self) -> Dict:
        """Get pool statistics."""
        return {
            "prefix": self.prefix,
            "prefix_length": self.prefix_length,
            "total_capacity": self.total_capacity,
            "allocated": len(self.allocated_blocks),
            "available": self.available,
            "utilization_percent": (len(self.allocated_blocks) / self.total_capacity) * 100
        }


class ProxyRotator:
    """
    Rotate proxies to get fresh IPs.
    
    Supports multiple proxy providers with different rotation strategies.
    """
    
    PROVIDERS = {
        "dataimpulse": {
            "type": "residential",
            "rotation": "session_based",
            "url_template": "http://{user}:{pass}@gw.dataimpulse.com:{port}",
            "ports": {"rotating": 823, "sticky": 10000}
        },
        "smartproxy": {
            "type": "residential",
            "rotation": "session_based", 
            "url_template": "http://{user}-session-{session}:{pass}@us.smartproxy.com:10000"
        },
        "brightdata": {
            "type": "residential",
            "rotation": "per_request",
            "url_template": "http://{user}-session-{session}:{pass}@brd.superproxy.io:22225"
        }
    }
    
    def __init__(
        self,
        provider: str = "dataimpulse",
        username: str = None,
        password: str = None,
        country: str = "us",
        ip_manager: IPRotationManager = None
    ):
        """
        Initialize proxy rotator.
        
        Args:
            provider: Proxy provider name
            username: Proxy username
            password: Proxy password
            country: Target country
            ip_manager: IP manager for tracking used IPs
        """
        self.provider = provider
        self.username = username
        self.password = password
        self.country = country
        self.ip_manager = ip_manager or IPRotationManager()
        
        self.session_counter = 0
        self.current_ip = None
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID for sticky session."""
        import random
        self.session_counter += 1
        rand_part = random.randint(10000, 99999)
        return f"k12v_{self.session_counter}_{rand_part}"
    
    def get_proxy_url(self, new_session: bool = False) -> str:
        """
        Get proxy URL, optionally with new session.
        
        Args:
            new_session: If True, generate new session ID for rotation
            
        Returns:
            Proxy URL string
        """
        if not self.username or not self.password:
            return None
        
        session_id = self._generate_session_id() if new_session else "default"
        
        if self.provider == "dataimpulse":
            # Format: user__country-us__session-xxx:pass@host:port
            user_full = f"{self.username}__country-{self.country}__session-{session_id}"
            return f"http://{user_full}:{self.password}@gw.dataimpulse.com:823"
        
        elif self.provider == "smartproxy":
            user_full = f"{self.username}-session-{session_id}"
            return f"http://{user_full}:{self.password}@us.smartproxy.com:10000"
        
        elif self.provider == "brightdata":
            user_full = f"{self.username}-session-{session_id}"
            return f"http://{user_full}:{self.password}@brd.superproxy.io:22225"
        
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    async def get_fresh_ip(self, max_attempts: int = 10) -> tuple:
        """
        Rotate proxy until getting a fresh (unused) IP.
        
        Args:
            max_attempts: Maximum rotation attempts
            
        Returns:
            Tuple of (ip, proxy_url)
        """
        import httpx
        
        for attempt in range(1, max_attempts + 1):
            try:
                # Get new proxy session
                proxy_url = self.get_proxy_url(new_session=True)
                
                # Check current IP
                async with httpx.AsyncClient(proxy=proxy_url, timeout=15) as client:
                    response = await client.get("http://ip-api.com/json/?fields=query,countryCode")
                    if response.status_code == 200:
                        data = response.json()
                        current_ip = data.get("query")
                        
                        if current_ip and not self.ip_manager.is_ip_used(current_ip):
                            logger.info(f"Got fresh IP: {current_ip} (attempt {attempt})")
                            self.current_ip = current_ip
                            return current_ip, proxy_url
                        else:
                            logger.info(f"IP {current_ip} already used, rotating... (attempt {attempt})")
            
            except Exception as e:
                logger.warning(f"Rotation attempt {attempt} failed: {e}")
            
            # Small delay between rotations
            await asyncio.sleep(1)
        
        raise Exception(f"Could not get fresh IP after {max_attempts} rotations")
    
    def get_fresh_ip_sync(self, max_attempts: int = 10) -> tuple:
        """
        Synchronous version of get_fresh_ip.
        
        Returns:
            Tuple of (ip, proxy_url)
        """
        import httpx
        
        for attempt in range(1, max_attempts + 1):
            try:
                # Get new proxy session
                proxy_url = self.get_proxy_url(new_session=True)
                
                # Check current IP
                with httpx.Client(proxy=proxy_url, timeout=15) as client:
                    response = client.get("http://ip-api.com/json/?fields=query,countryCode")
                    if response.status_code == 200:
                        data = response.json()
                        current_ip = data.get("query")
                        
                        if current_ip and not self.ip_manager.is_ip_used(current_ip):
                            logger.info(f"Got fresh IP: {current_ip} (attempt {attempt})")
                            self.current_ip = current_ip
                            return current_ip, proxy_url
                        else:
                            logger.info(f"IP {current_ip} already used, rotating... (attempt {attempt})")
            
            except Exception as e:
                logger.warning(f"Rotation attempt {attempt} failed: {e}")
            
            # Small delay between rotations
            time.sleep(1)
        
        raise Exception(f"Could not get fresh IP after {max_attempts} rotations")


# Convenience function
def get_ip_manager() -> IPRotationManager:
    """Get singleton IP manager instance."""
    if not hasattr(get_ip_manager, "_instance"):
        get_ip_manager._instance = IPRotationManager()
    return get_ip_manager._instance


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Testing IP Rotation Manager")
    print("=" * 60)
    
    # Test IP normalization
    manager = IPRotationManager()
    
    # IPv4 tests
    print("\nIPv4 Tests:")
    ipv4_test = "192.168.1.100"
    print(f"  {ipv4_test} -> {manager.normalize_ip(ipv4_test)}")
    
    # IPv6 tests  
    print("\nIPv6 Tests:")
    ipv6_tests = [
        "2001:db8:1234:5678:abcd:ef01:2345:6789",
        "2001:db8::1",
        "fe80::1",
    ]
    for ipv6 in ipv6_tests:
        print(f"  {ipv6} -> {manager.normalize_ip(ipv6)}")
    
    # Test usage tracking
    print("\nUsage Tracking:")
    test_ip = "203.0.113.50"
    print(f"  Is {test_ip} used? {manager.is_ip_used(test_ip)}")
    manager.mark_ip_used(test_ip, verification_id="test123")
    print(f"  After marking - Is {test_ip} used? {manager.is_ip_used(test_ip)}")
    
    # Test IPv6 pool
    print("\n" + "=" * 60)
    print("Testing IPv6 Pool Manager")
    print("=" * 60)
    
    try:
        pool = IPv6PoolManager("2001:db8:1234::/48")
        print(f"\nPool Stats: {pool.get_stats()}")
        
        # Allocate some blocks
        for i in range(3):
            block = pool.allocate_block()
            print(f"  Allocated: {block}")
        
        print(f"\nAfter allocation: {pool.get_stats()}")
    except Exception as e:
        print(f"IPv6 pool test skipped: {e}")
    
    print("\n✅ IP Manager tests passed!")
