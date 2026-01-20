"""SheerID 学生验证主程序"""
import re
import random
import logging
import time
from typing import Dict, Optional, Tuple

# Use curl_cffi for TLS fingerprint impersonation (bypass bot detection)
try:
    from curl_cffi import requests as curl_requests
    CURL_AVAILABLE = True
except ImportError:
    curl_requests = None
    CURL_AVAILABLE = False
    import httpx

# Import proxy manager for rotating proxies
try:
    from config.proxy_manager import get_proxy_url
except ImportError:
    def get_proxy_url():
        return None

from . import config
from .name_generator import NameGenerator, generate_birth_date
from .img_generator import generate_image, generate_psu_email

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SheerIDVerifier:
    """SheerID 学生身份验证器"""

    def __init__(self, verification_id: str):
        self.verification_id = verification_id
        self.device_fingerprint = self._generate_device_fingerprint()
        self._proxy_url = get_proxy_url()
        
        # Use curl_cffi for TLS fingerprint impersonation
        if CURL_AVAILABLE:
            self.http_client = curl_requests.Session(
                impersonate="chrome120",
                timeout=30,
                proxies={"http": self._proxy_url, "https": self._proxy_url} if self._proxy_url else None
            )
            logger.info(f"Using curl_cffi with Chrome120 TLS fingerprint" + 
                       (f" via proxy" if self._proxy_url else ""))
        else:
            import httpx
            self.http_client = httpx.Client(timeout=30.0, proxy=self._proxy_url)
            logger.info(f"Using httpx (curl_cffi not available)" + 
                       (f" via proxy" if self._proxy_url else ""))

    def __del__(self):
        if hasattr(self, "http_client") and self.http_client:
            try:
                self.http_client.close()
            except Exception:
                pass

    @staticmethod
    def _generate_device_fingerprint() -> str:
        """Generate realistic device fingerprint using FingerprintGenerator."""
        try:
            from .fingerprint_generator import FingerprintGenerator
            fp = FingerprintGenerator.generate(os_type="windows", browser="chrome")
            # Create fingerprint hash from profile
            import hashlib
            fp_string = f"{fp.user_agent}{fp.webgl_renderer}{fp.screen_width}{fp.timezone}"
            return hashlib.md5(fp_string.encode()).hexdigest()
        except ImportError:
            # Fallback to random hex
            chars = '0123456789abcdef'
            return ''.join(random.choice(chars) for _ in range(32))

    @staticmethod
    def normalize_url(url: str) -> str:
        """规范化 URL（保留原样）"""
        return url

    @staticmethod
    def parse_verification_id(url: str) -> Optional[str]:
        match = re.search(r"verificationId=([a-f0-9]+)", url, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _get_browser_fingerprint(self):
        """Get or create browser fingerprint for consistent headers."""
        if not hasattr(self, '_fingerprint'):
            try:
                from .fingerprint_generator import FingerprintGenerator
                self._fingerprint = FingerprintGenerator.generate(os_type="windows")
            except ImportError:
                self._fingerprint = None
        return self._fingerprint

    def _sheerid_request(
        self, method: str, url: str, body: Optional[Dict] = None
    ) -> Tuple[Dict, int]:
        """发送 SheerID API 请求 with anti-detection headers"""
        
        # Get fingerprint for consistent headers
        fp = self._get_browser_fingerprint()
        
        # Build realistic Chrome headers
        if fp:
            chrome_version = fp.browser_version.split('.')[0]
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": f"{fp.language},{fp.languages[0].split('-')[0]};q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Ch-Ua": f'"Not_A Brand";v="8", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": f'"{fp.os_name}"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": fp.user_agent,
                "Origin": config.SHEERID_BASE_URL,
                "Referer": f"{config.SHEERID_BASE_URL}/verify/{config.PROGRAM_ID}/",
            }
        else:
            # Fallback headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
        
        # Add human-like delay
        time.sleep(random.uniform(0.3, 1.0))

        try:
            response = self.http_client.request(
                method=method, url=url, json=body, headers=headers
            )
            try:
                data = response.json()
            except Exception:
                data = response.text
            return data, response.status_code
        except Exception as e:
            logger.error(f"SheerID request failed: {e}")
            raise

    def _upload_to_s3(self, upload_url: str, img_data: bytes) -> bool:
        """上传 PNG 到 S3"""
        try:
            headers = {"Content-Type": "image/png"}
            # curl_cffi uses 'data', httpx uses 'content'
            if CURL_AVAILABLE:
                response = self.http_client.put(
                    upload_url, data=img_data, headers=headers, timeout=60
                )
            else:
                response = self.http_client.put(
                    upload_url, content=img_data, headers=headers, timeout=60.0
                )
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def verify(
        self,
        first_name: str = None,
        last_name: str = None,
        email: str = None,
        birth_date: str = None,
        school_id: str = None,
        progress_callback=None,
    ) -> Dict:
        """执行验证流程
        
        Args:
            progress_callback: Optional callable(step: int, total: int, message: str)
                              Called to report progress during verification
        """
        def report_progress(step: int, total: int, message: str):
            """Report progress to callback if provided"""
            logger.info(f"Step {step}/{total}: {message}")
            if progress_callback:
                try:
                    progress_callback(step, total, message)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")
        
        try:
            current_step = "initial"

            if not first_name or not last_name:
                name = NameGenerator.generate()
                first_name = name["first_name"]
                last_name = name["last_name"]

            school_id = school_id or config.DEFAULT_SCHOOL_ID
            school = config.SCHOOLS[school_id]

            if not email:
                email = generate_psu_email(first_name, last_name)
            if not birth_date:
                birth_date = generate_birth_date()

            logger.info(f"Student info: {first_name} {last_name}")
            logger.info(f"Email: {email}")
            logger.info(f"School: {school['name']}")
            logger.info(f"Birth date: {birth_date}")
            logger.info(f"Verification ID: {self.verification_id}")

            # Generate student ID PNG
            report_progress(1, 4, "Generating student ID document...")
            img_data = generate_image(first_name, last_name, school_id)
            file_size = len(img_data)
            logger.info(f"✅ PNG size: {file_size / 1024:.2f}KB")

            # Add human-like delay before submitting (simulating form filling)
            form_delay = random.uniform(3.0, 6.0)
            logger.info(f"⏳ Waiting {form_delay:.1f}s before submitting (simulating form filling)...")
            time.sleep(form_delay)

            # Submit student info
            report_progress(2, 4, "Submitting student info...")
            step2_body = {
                "firstName": first_name,
                "lastName": last_name,
                "birthDate": birth_date,
                "email": email,
                "phoneNumber": "",
                "organization": {
                    "id": int(school_id),
                    "idExtended": school["idExtended"],
                    "name": school["name"],
                },
                "deviceFingerprintHash": self.device_fingerprint,
                "locale": "en-US",
                "metadata": {
                    "marketConsentValue": False,
                    "refererUrl": f"{config.SHEERID_BASE_URL}/verify/{config.PROGRAM_ID}/?verificationId={self.verification_id}",
                    "verificationId": self.verification_id,
                    "flags": '{"collect-info-step-email-first":"default","doc-upload-considerations":"default","doc-upload-may24":"default","doc-upload-redesign-use-legacy-message-keys":false,"docUpload-assertion-checklist":"default","font-size":"default","include-cvec-field-france-student":"not-labeled-optional"}',
                    "submissionOptIn": "By submitting the personal information above, I acknowledge that my personal information is being collected under the privacy policy of the business from which I am seeking a discount",
                },
            }

            step2_data, step2_status = self._sheerid_request(
                "POST",
                f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/collectStudentPersonalInfo",
                step2_body,
            )

            if step2_status != 200:
                raise Exception(f"Step 2 failed (status {step2_status}): {step2_data}")
            if step2_data.get("currentStep") == "error":
                error_msg = ", ".join(step2_data.get("errorIds", ["Unknown error"]))
                raise Exception(f"Step 2 error: {error_msg}")

            logger.info(f"✅ Step 2 complete: {step2_data.get('currentStep')}")
            current_step = step2_data.get("currentStep", current_step)

            # Skip SSO (if required)
            if current_step in ["sso", "collectStudentPersonalInfo"]:
                report_progress(3, 4, "Bypassing SSO verification...")
                step3_data, _ = self._sheerid_request(
                    "DELETE",
                    f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/sso",
                )
                logger.info(f"✅ Step 3 complete: {step3_data.get('currentStep')}")
                current_step = step3_data.get("currentStep", current_step)

            # Add delay before document upload
            upload_delay = random.uniform(2.0, 4.0)
            logger.info(f"⏳ Waiting {upload_delay:.1f}s before document upload...")
            time.sleep(upload_delay)

            # Upload document and complete submission
            report_progress(4, 4, "Uploading document to SheerID...")
            step4_body = {
                "files": [
                    {"fileName": "student_card.png", "mimeType": "image/png", "fileSize": file_size}
                ]
            }
            step4_data, step4_status = self._sheerid_request(
                "POST",
                f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/docUpload",
                step4_body,
            )
            if not step4_data.get("documents"):
                raise Exception("Failed to get upload URL")

            upload_url = step4_data["documents"][0]["uploadUrl"]
            logger.info("✅ Got upload URL successfully")
            if not self._upload_to_s3(upload_url, img_data):
                raise Exception("S3 upload failed")
            logger.info("✅ Student ID uploaded successfully")

            step6_data, _ = self._sheerid_request(
                "POST",
                f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/completeDocUpload",
            )
            logger.info(f"✅ Document submission complete: {step6_data.get('currentStep')}")
            final_status = step6_data

            # Return with student info for display
            return {
                "success": True,
                "pending": True,
                "message": "Document submitted, awaiting review",
                "verification_id": self.verification_id,
                "redirect_url": final_status.get("redirectUrl"),
                "status": final_status,
                "student_info": {
                    "name": f"{first_name} {last_name}",
                    "email": email,
                    "birth_date": birth_date,
                    "school": school["name"]
                }
            }

        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return {
                "success": False, 
                "message": str(e), 
                "verification_id": self.verification_id,
                "student_info": {
                    "name": f"{first_name} {last_name}" if first_name and last_name else "N/A",
                    "email": email if email else "N/A",
                    "birth_date": birth_date if birth_date else "N/A",
                    "school": school["name"] if school else "N/A"
                }
            }


def main():
    """主函数 - 命令行界面"""
    import sys

    print("="  * 60)
    print("SheerID Student Verification Tool (Python)")
    print("=" * 60)
    print()

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter SheerID verification URL: ").strip()

    if not url:
        print("❌ Error: No URL provided")
        sys.exit(1)

    verification_id = SheerIDVerifier.parse_verification_id(url)
    if not verification_id:
        print("❌ Error: Invalid verification ID format")
        sys.exit(1)

    print(f"✅ Parsed verification ID: {verification_id}")
    print()

    verifier = SheerIDVerifier(verification_id)
    result = verifier.verify()

    print()
    print("=" * 60)
    print("Result:")
    print("=" * 60)
    print(f"Status: {'✅ Success' if result['success'] else '❌ Failed'}")
    print(f"Message: {result['message']}")
    if result.get("redirect_url"):
        print(f"Redirect URL: {result['redirect_url']}")
    print("=" * 60)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
