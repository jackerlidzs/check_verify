"""
Browser Fingerprint Generator for Anti-Detection

Generates realistic, consistent browser fingerprints similar to Dolphin Browser.
Each fingerprint includes all parameters needed to spoof browser identity.

Usage:
    from fingerprint_generator import FingerprintGenerator
    
    # Generate random fingerprint
    fp = FingerprintGenerator.generate()
    
    # Generate with specific OS/browser
    fp = FingerprintGenerator.generate(os_type="windows", browser="chrome")
    
    # Generate with seed for consistency
    fp = FingerprintGenerator.generate(seed="my-session-123")
"""
import random
import hashlib
import json
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class BrowserFingerprint:
    """Complete browser fingerprint profile."""
    
    # === Identification ===
    profile_id: str = ""
    seed: str = ""
    
    # === Platform & OS ===
    platform: str = "Win32"                    # Win32, MacIntel, Linux x86_64
    os_name: str = "Windows"                   # Windows, macOS, Linux
    os_version: str = "10"                     # 10, 11, 14.0 (Sonoma)
    
    # === User Agent ===
    user_agent: str = ""
    browser_name: str = "Chrome"
    browser_version: str = "120.0.0.0"
    
    # === Screen ===
    screen_width: int = 1920
    screen_height: int = 1080
    screen_avail_width: int = 1920
    screen_avail_height: int = 1040
    color_depth: int = 24
    pixel_depth: int = 24
    device_pixel_ratio: float = 1.0
    
    # === Hardware ===
    hardware_concurrency: int = 8              # CPU cores
    device_memory: int = 8                     # GB RAM
    max_touch_points: int = 0                  # 0 for desktop
    
    # === Browser Info ===
    vendor: str = "Google Inc."
    vendor_sub: str = ""
    product: str = "Gecko"
    product_sub: str = "20030107"
    app_name: str = "Netscape"
    app_code_name: str = "Mozilla"
    app_version: str = ""
    
    # === Language & Locale ===
    language: str = "en-US"
    languages: List[str] = field(default_factory=lambda: ["en-US", "en"])
    
    # === Timezone ===
    timezone: str = "America/New_York"
    timezone_offset: int = 300                 # Minutes from UTC (EST = 300)
    
    # === WebGL ===
    webgl_vendor: str = "Google Inc. (Intel)"
    webgl_renderer: str = "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    webgl_version: str = "WebGL 1.0 (OpenGL ES 2.0 Chromium)"
    webgl2_version: str = "WebGL 2.0 (OpenGL ES 3.0 Chromium)"
    
    # === Canvas ===
    canvas_noise_seed: int = 0                 # Seed for consistent noise
    canvas_noise_factor: float = 0.0001        # How much noise to add
    
    # === Audio ===
    audio_context_sample_rate: int = 44100
    audio_noise_seed: int = 0
    audio_noise_factor: float = 0.0001
    
    # === WebRTC ===
    webrtc_mode: str = "altered"               # disabled, altered, real
    webrtc_local_ip: str = "192.168.1.100"     # Spoofed local IP
    
    # === Media Devices ===
    media_devices: List[Dict] = field(default_factory=list)
    
    # === Plugins ===
    plugins_count: int = 5
    
    # === Misc ===
    do_not_track: Optional[str] = None         # "1", None
    cookie_enabled: bool = True
    java_enabled: bool = False
    pdf_viewer_enabled: bool = True
    
    # === Client Rects ===
    client_rects_noise_seed: int = 0
    client_rects_noise_factor: float = 0.00001
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BrowserFingerprint':
        """Create from dictionary."""
        return cls(**data)


class FingerprintGenerator:
    """
    Generate realistic browser fingerprints.
    
    Uses real-world browser statistics for authentic profiles.
    """
    
    # === User Agent Templates ===
    UA_TEMPLATES = {
        "chrome_windows": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
        ],
        "chrome_macos": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
        ],
        "chrome_linux": [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
        ],
        "firefox_windows": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/{version}",
        ],
        "edge_windows": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36 Edg/{version}",
        ],
        # === Android Mobile User Agents ===
        "chrome_android": [
            # Samsung Galaxy S series
            "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
            # Google Pixel
            "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
            # OnePlus
            "Mozilla/5.0 (Linux; Android 14; CPH2451) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; LE2125) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
            # Xiaomi
            "Mozilla/5.0 (Linux; Android 14; 2312DRA50G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; 2211133C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Mobile Safari/537.36",
        ],
    }
    
    # === Chrome Versions (recent, stable) ===
    CHROME_VERSIONS = [
        "120.0.0.0", "121.0.0.0", "122.0.0.0", "123.0.0.0",
        "124.0.0.0", "125.0.0.0", "126.0.0.0", "127.0.0.0",
        "128.0.0.0", "129.0.0.0", "130.0.0.0", "131.0.0.0",
        "132.0.0.0", "133.0.0.0", "134.0.0.0", "135.0.0.0",
        "136.0.0.0", "137.0.0.0", "138.0.0.0", "139.0.0.0",
        "140.0.0.0", "141.0.0.0", "142.0.0.0", "143.0.0.0",
    ]
    
    # === Screen Resolutions (weighted by popularity) ===
    SCREEN_RESOLUTIONS = [
        # (width, height, weight)
        (1920, 1080, 35),   # Full HD - most common
        (1366, 768, 20),    # HD - laptops
        (1536, 864, 12),    # Scaled HD
        (1440, 900, 8),     # MacBook
        (1280, 720, 7),     # HD
        (2560, 1440, 8),    # QHD
        (1680, 1050, 4),    # WSXGA+
        (1600, 900, 3),     # HD+
        (3840, 2160, 3),    # 4K
    ]
    
    # === Android Screen Resolutions ===
    ANDROID_SCREEN_RESOLUTIONS = [
        # (width, height, weight) - portrait mode
        (1080, 2340, 25),   # FHD+ 19.5:9 (Samsung S21, most common)
        (1080, 2400, 25),   # FHD+ 20:9 (Pixel 7, OnePlus)
        (1440, 3088, 15),   # QHD+ (Samsung S23 Ultra)
        (1440, 3120, 10),   # QHD+ (Samsung S22 Ultra)
        (1344, 2992, 10),   # Pixel 8 Pro
        (1080, 2412, 8),    # Pixel 7/8
        (1080, 2376, 5),    # OnePlus 11
        (1284, 2778, 2),    # (for testing variety)
    ]
    
    # === Hardware Concurrency (CPU cores) ===
    HARDWARE_CONCURRENCY = [
        (4, 30),   # Quad-core - most common
        (8, 35),   # Octa-core
        (6, 15),   # Hexa-core
        (12, 10),  # 12 threads
        (16, 8),   # High-end
        (2, 2),    # Dual-core (old)
    ]
    
    # === Device Memory (GB) ===
    DEVICE_MEMORY = [
        (8, 40),   # 8GB - most common
        (16, 30),  # 16GB
        (4, 15),   # 4GB - lower end
        (32, 10),  # 32GB - high end
        (2, 5),    # 2GB - very low
    ]
    
    # === WebGL Profiles ===
    WEBGL_PROFILES = [
        # Intel Integrated
        {
            "vendor": "Google Inc. (Intel)",
            "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "os": ["windows"],
            "weight": 20
        },
        {
            "vendor": "Google Inc. (Intel)",
            "renderer": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "os": ["windows"],
            "weight": 15
        },
        {
            "vendor": "Google Inc. (Intel)",
            "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "os": ["windows"],
            "weight": 10
        },
        # NVIDIA
        {
            "vendor": "Google Inc. (NVIDIA)",
            "renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "os": ["windows"],
            "weight": 8
        },
        {
            "vendor": "Google Inc. (NVIDIA)",
            "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "os": ["windows"],
            "weight": 10
        },
        {
            "vendor": "Google Inc. (NVIDIA)",
            "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "os": ["windows"],
            "weight": 5
        },
        # AMD
        {
            "vendor": "Google Inc. (AMD)",
            "renderer": "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "os": ["windows"],
            "weight": 6
        },
        {
            "vendor": "Google Inc. (AMD)",
            "renderer": "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "os": ["windows"],
            "weight": 5
        },
        # macOS
        {
            "vendor": "Google Inc. (Apple)",
            "renderer": "ANGLE (Apple, Apple M1, OpenGL 4.1)",
            "os": ["macos"],
            "weight": 12
        },
        {
            "vendor": "Google Inc. (Apple)",
            "renderer": "ANGLE (Apple, Apple M2, OpenGL 4.1)",
            "os": ["macos"],
            "weight": 8
        },
        {
            "vendor": "Google Inc. (Apple)",
            "renderer": "ANGLE (Apple, Apple M3, OpenGL 4.1)",
            "os": ["macos"],
            "weight": 5
        },
        # Linux (Mesa)
        {
            "vendor": "Google Inc. (Intel)",
            "renderer": "ANGLE (Intel, Mesa Intel(R) UHD Graphics 630 (CFL GT2), OpenGL 4.6)",
            "os": ["linux"],
            "weight": 5
        },
        # === Android GPUs ===
        # Qualcomm Adreno (Samsung, OnePlus, Xiaomi)
        {
            "vendor": "Qualcomm",
            "renderer": "Adreno (TM) 740",
            "os": ["android"],
            "weight": 25
        },
        {
            "vendor": "Qualcomm",
            "renderer": "Adreno (TM) 730",
            "os": ["android"],
            "weight": 20
        },
        {
            "vendor": "Qualcomm",
            "renderer": "Adreno (TM) 650",
            "os": ["android"],
            "weight": 15
        },
        {
            "vendor": "Qualcomm",
            "renderer": "Adreno (TM) 660",
            "os": ["android"],
            "weight": 12
        },
        # ARM Mali (Samsung Exynos, MediaTek)
        {
            "vendor": "ARM",
            "renderer": "Mali-G715 MC11",
            "os": ["android"],
            "weight": 10
        },
        {
            "vendor": "ARM",
            "renderer": "Mali-G78 MP20",
            "os": ["android"],
            "weight": 8
        },
        {
            "vendor": "ARM",
            "renderer": "Mali-G710 MC10",
            "os": ["android"],
            "weight": 6
        },
        # Google Tensor (Pixel)
        {
            "vendor": "ARM",
            "renderer": "Mali-G710",
            "os": ["android"],
            "weight": 8
        },
    ]
    
    # === Timezones (US focused) ===
    TIMEZONES = [
        ("America/New_York", -300, 25),      # EST
        ("America/Chicago", -360, 15),       # CST
        ("America/Denver", -420, 10),        # MST
        ("America/Los_Angeles", -480, 20),   # PST
        ("America/Phoenix", -420, 5),        # No DST
        ("America/Anchorage", -540, 3),      # Alaska
        ("Pacific/Honolulu", -600, 2),       # Hawaii
    ]
    
    # === Language Combinations ===
    LANGUAGES = [
        (["en-US", "en"], 60),
        (["en-US"], 25),
        (["en-US", "en", "es"], 5),
        (["en-GB", "en"], 5),
        (["en-AU", "en"], 3),
        (["en-CA", "en", "fr"], 2),
    ]
    
    @classmethod
    def _weighted_choice(cls, items: List[Tuple], rng: random.Random) -> any:
        """Select item based on weights."""
        total = sum(item[-1] for item in items)
        r = rng.uniform(0, total)
        upto = 0
        for item in items:
            weight = item[-1]
            if upto + weight >= r:
                return item[:-1] if len(item) > 2 else item[0]
            upto += weight
        return items[-1][:-1] if len(items[-1]) > 2 else items[-1][0]
    
    @classmethod
    def generate(
        cls,
        os_type: str = None,
        browser: str = "chrome",
        seed: str = None,
        webrtc_mode: str = "altered"
    ) -> BrowserFingerprint:
        """
        Generate a complete browser fingerprint.
        
        Args:
            os_type: "windows", "macos", "linux", or None for random
            browser: "chrome", "firefox", "edge"
            seed: Optional seed for reproducibility
            webrtc_mode: "disabled", "altered", "real"
            
        Returns:
            BrowserFingerprint instance
        """
        # Initialize RNG with seed
        if seed:
            seed_hash = hashlib.md5(seed.encode()).hexdigest()
            rng = random.Random(int(seed_hash[:8], 16))
        else:
            rng = random.Random()
            seed = hashlib.md5(str(rng.random()).encode()).hexdigest()[:16]
        
        # Generate profile ID
        profile_id = hashlib.md5(seed.encode()).hexdigest()[:12]
        
        # Select OS if not specified
        if os_type is None:
            os_type = rng.choices(
                ["windows", "macos", "linux", "android"],
                weights=[70, 18, 4, 8]  # Include Android
            )[0]
        
        # === Platform & OS ===
        is_mobile = os_type == "android"
        
        if os_type == "windows":
            platform = "Win32"
            os_name = "Windows"
            os_version = rng.choice(["10", "11"])
        elif os_type == "macos":
            platform = "MacIntel"
            os_name = "macOS"
            os_version = rng.choice(["10_15_7", "13_0", "14_0"])
        elif os_type == "android":
            platform = "Linux armv81"  # ARM Android
            os_name = "Android"
            os_version = rng.choice(["13", "14"])  # Android 13-14
        else:
            platform = "Linux x86_64"
            os_name = "Linux"
            os_version = ""
        
        # === Browser Version ===
        browser_version = rng.choice(cls.CHROME_VERSIONS)
        
        # === User Agent ===
        ua_key = f"{browser}_{os_type}"
        ua_templates = cls.UA_TEMPLATES.get(ua_key, cls.UA_TEMPLATES["chrome_windows"])
        ua_template = rng.choice(ua_templates)
        user_agent = ua_template.format(version=browser_version, chrome_version=browser_version)
        
        # === Screen ===
        if is_mobile:
            # Use Android screen resolutions
            screen_width, screen_height = cls._weighted_choice(
                [(r[0], r[1], r[2]) for r in cls.ANDROID_SCREEN_RESOLUTIONS], rng
            )
            # Mobile has full screen available (no taskbar)
            screen_avail_height = screen_height
            screen_avail_width = screen_width
        else:
            screen_width, screen_height = cls._weighted_choice(
                [(r[0], r[1], r[2]) for r in cls.SCREEN_RESOLUTIONS], rng
            )
            # Available height is slightly less (taskbar)
            screen_avail_height = screen_height - rng.randint(40, 80)
            screen_avail_width = screen_width
        
        # Color/Pixel depth
        color_depth = rng.choice([24, 24, 24, 32])  # 24 is most common
        pixel_depth = color_depth
        
        # Device pixel ratio
        if is_mobile:
            # Mobile devices have higher DPR
            device_pixel_ratio = rng.choice([2.0, 2.5, 3.0, 3.5])
        elif screen_width >= 2560:
            device_pixel_ratio = rng.choice([1.0, 1.25, 1.5, 2.0])
        else:
            device_pixel_ratio = rng.choice([1.0, 1.0, 1.0, 1.25])
        
        # === Hardware ===
        if is_mobile:
            # Android devices typically have 8 cores
            hardware_concurrency = rng.choice([8, 8, 8, 6, 4])
            device_memory = rng.choice([8, 8, 12, 12, 16, 6, 4])  # GB RAM
            max_touch_points = rng.choice([5, 10, 10, 10])  # Mobile has touch
        else:
            hardware_concurrency = cls._weighted_choice(cls.HARDWARE_CONCURRENCY, rng)
            device_memory = cls._weighted_choice(cls.DEVICE_MEMORY, rng)
            max_touch_points = 0 if os_type != "macos" else rng.choice([0, 0, 0, 5])
        
        # === WebGL ===
        valid_webgl = [p for p in cls.WEBGL_PROFILES if os_type in p["os"]]
        if not valid_webgl:
            valid_webgl = cls.WEBGL_PROFILES[:3]  # Fallback to Intel
        
        webgl_profile = cls._weighted_choice(
            [(p["vendor"], p["renderer"], p["weight"]) for p in valid_webgl], rng
        )
        webgl_vendor, webgl_renderer = webgl_profile
        
        # === Timezone ===
        tz_data = cls._weighted_choice(cls.TIMEZONES, rng)
        timezone, timezone_offset = tz_data
        
        # === Languages ===
        languages = cls._weighted_choice(cls.LANGUAGES, rng)
        if isinstance(languages, str):
            languages = [languages]
        language = languages[0]
        
        # === Canvas/Audio Noise Seeds ===
        canvas_noise_seed = rng.randint(1, 2**31)
        audio_noise_seed = rng.randint(1, 2**31)
        client_rects_noise_seed = rng.randint(1, 2**31)
        
        # === WebRTC ===
        webrtc_local_ip = f"192.168.{rng.randint(0,255)}.{rng.randint(1,254)}"
        
        # === Media Devices ===
        media_devices = []
        # Add some fake devices
        if rng.random() > 0.3:  # 70% have webcam
            media_devices.append({
                "deviceId": hashlib.md5(f"{seed}-video".encode()).hexdigest()[:32],
                "kind": "videoinput",
                "label": rng.choice([
                    "Integrated Webcam",
                    "HD Webcam", 
                    "USB Camera",
                    "Logitech HD Webcam C920"
                ])
            })
        if rng.random() > 0.2:  # 80% have microphone
            media_devices.append({
                "deviceId": hashlib.md5(f"{seed}-audio".encode()).hexdigest()[:32],
                "kind": "audioinput",
                "label": rng.choice([
                    "Microphone (Realtek Audio)",
                    "Internal Microphone",
                    "Microphone Array (Intel)",
                    "Default - Microphone"
                ])
            })
        # Audio output
        media_devices.append({
            "deviceId": hashlib.md5(f"{seed}-speaker".encode()).hexdigest()[:32],
            "kind": "audiooutput",
            "label": rng.choice([
                "Speakers (Realtek Audio)",
                "Speakers (High Definition Audio)",
                "Headphones"
            ])
        })
        
        # === Build Fingerprint ===
        return BrowserFingerprint(
            profile_id=profile_id,
            seed=seed,
            
            # Platform
            platform=platform,
            os_name=os_name,
            os_version=os_version,
            
            # User Agent
            user_agent=user_agent,
            browser_name=browser.capitalize(),
            browser_version=browser_version,
            
            # Screen
            screen_width=screen_width,
            screen_height=screen_height,
            screen_avail_width=screen_avail_width,
            screen_avail_height=screen_avail_height,
            color_depth=color_depth,
            pixel_depth=pixel_depth,
            device_pixel_ratio=device_pixel_ratio,
            
            # Hardware
            hardware_concurrency=hardware_concurrency,
            device_memory=device_memory,
            max_touch_points=max_touch_points,
            
            # Browser
            vendor="Google Inc." if browser == "chrome" else "Mozilla",
            app_version=f"5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{browser_version} Safari/537.36",
            
            # Language
            language=language,
            languages=languages,
            
            # Timezone
            timezone=timezone,
            timezone_offset=timezone_offset,
            
            # WebGL
            webgl_vendor=webgl_vendor,
            webgl_renderer=webgl_renderer,
            
            # Canvas
            canvas_noise_seed=canvas_noise_seed,
            canvas_noise_factor=0.0001,
            
            # Audio
            audio_noise_seed=audio_noise_seed,
            audio_noise_factor=0.0001,
            
            # WebRTC
            webrtc_mode=webrtc_mode,
            webrtc_local_ip=webrtc_local_ip,
            
            # Media
            media_devices=media_devices,
            
            # Misc
            plugins_count=rng.randint(3, 7),
            do_not_track=rng.choice([None, None, "1"]),
            cookie_enabled=True,
            
            # Client Rects
            client_rects_noise_seed=client_rects_noise_seed,
            client_rects_noise_factor=0.00001,
        )
    
    @classmethod
    def generate_batch(cls, count: int, **kwargs) -> List[BrowserFingerprint]:
        """Generate multiple unique fingerprints."""
        return [cls.generate(**kwargs) for _ in range(count)]


def test_fingerprint():
    """Test fingerprint generation."""
    print("=" * 60)
    print("Testing Fingerprint Generator")
    print("=" * 60)
    
    # Test 1: Random fingerprint
    print("\n1. Random fingerprint:")
    fp = FingerprintGenerator.generate()
    print(f"   Profile ID: {fp.profile_id}")
    print(f"   OS: {fp.os_name} {fp.os_version}")
    print(f"   Screen: {fp.screen_width}x{fp.screen_height}")
    print(f"   CPU: {fp.hardware_concurrency} cores")
    print(f"   RAM: {fp.device_memory} GB")
    print(f"   WebGL: {fp.webgl_renderer[:50]}...")
    print(f"   Timezone: {fp.timezone}")
    
    # Test 2: Seeded fingerprint (consistent)
    print("\n2. Seeded fingerprint (should be same each time):")
    fp1 = FingerprintGenerator.generate(seed="test-session-123")
    fp2 = FingerprintGenerator.generate(seed="test-session-123")
    print(f"   FP1 Profile: {fp1.profile_id}")
    print(f"   FP2 Profile: {fp2.profile_id}")
    print(f"   Match: {fp1.profile_id == fp2.profile_id}")
    
    # Test 3: Windows specific
    print("\n3. Windows fingerprint:")
    fp_win = FingerprintGenerator.generate(os_type="windows")
    print(f"   Platform: {fp_win.platform}")
    print(f"   UA: {fp_win.user_agent[:60]}...")
    
    # Test 4: macOS specific
    print("\n4. macOS fingerprint:")
    fp_mac = FingerprintGenerator.generate(os_type="macos")
    print(f"   Platform: {fp_mac.platform}")
    print(f"   WebGL: {fp_mac.webgl_renderer}")
    
    print("\n" + "=" * 60)
    print("✅ Fingerprint Generator working!")
    print("=" * 60)


if __name__ == "__main__":
    test_fingerprint()
