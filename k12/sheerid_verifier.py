"""SheerID K12 Teacher Verification with Auto-Retry

Full flow:
1. Fill form -> Submit
2. SSO -> Skip
3. docUpload -> Generate ID Card -> Upload -> Submit
4. Poll status for ~8 minutes
5. If REJECTED -> Retry with blank image 3 times -> Retry with new profile
6. If APPROVED -> Return redirect link
"""
import re
import random
import logging
import time
import httpx
from typing import Dict, Optional, Tuple, Literal

# Import consistent generator
try:
    from .img_generator import TeacherDocumentData
except ImportError:
    from img_generator import TeacherDocumentData

# Document type enum
DocumentType = Literal["hr_system", "id_card", "blank", "none"]

# 支持既作为包导入又直接脚本运行
try:
    from . import config  # type: ignore
    from .name_generator import NameGenerator, generate_email, generate_birth_date, get_random_teacher_profile, generate_teacher_info  # type: ignore
    from .img_generator import generate_teacher_png  # type: ignore
except ImportError:
    import config  # type: ignore
    from name_generator import NameGenerator, generate_email, generate_birth_date, get_random_teacher_profile, generate_teacher_info  # type: ignore
    from img_generator import generate_teacher_png  # type: ignore

# 导入配置常量
PROGRAM_ID = config.PROGRAM_ID
SHEERID_BASE_URL = config.SHEERID_BASE_URL
MY_SHEERID_URL = config.MY_SHEERID_URL
SCHOOLS = config.SCHOOLS
DEFAULT_SCHOOL_ID = config.DEFAULT_SCHOOL_ID

# Retry configuration
MAX_STATUS_CHECKS = 16  # Check every 30s for ~8 minutes
STATUS_CHECK_INTERVAL = 30  # seconds
MAX_BLANK_RETRIES = 3  # Retry with blank image
MAX_PROFILE_RETRIES = 3  # Retry with different profiles

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SheerIDVerifier:
    """SheerID 教师身份验证器 with Auto-Retry"""

    def __init__(self, verification_id: str):
        self.verification_id = verification_id
        self.device_fingerprint = self._generate_device_fingerprint()
        self.http_client = httpx.Client(timeout=30.0)

    def __del__(self):
        if hasattr(self, 'http_client'):
            self.http_client.close()

    @staticmethod
    def _generate_device_fingerprint() -> str:
        chars = '0123456789abcdef'
        return ''.join(random.choice(chars) for _ in range(32))

    @staticmethod
    def normalize_url(url: str) -> str:
        return url

    @staticmethod
    def parse_verification_id(url: str) -> Optional[str]:
        match = re.search(r'verificationId=([a-f0-9]+)', url, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _sheerid_request(self, method: str, url: str,
                         body: Optional[Dict] = None) -> Tuple[Dict, int]:
        headers = {'Content-Type': 'application/json'}
        try:
            response = self.http_client.request(
                method=method, url=url, json=body, headers=headers
            )
            try:
                data = response.json()
            except Exception:
                data = {"raw": response.text}
            return data, response.status_code
        except Exception as e:
            logger.error(f"SheerID request failed: {e}")
            raise

    def _upload_to_s3(self, upload_url: str, content: bytes, mime_type: str) -> bool:
        try:
            headers = {'Content-Type': mime_type}
            response = self.http_client.put(
                upload_url, content=content, headers=headers, timeout=60.0
            )
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def check_status(self) -> Dict:
        """Check current verification status"""
        data, status = self._sheerid_request(
            'GET',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}"
        )
        return {
            'current_step': data.get('currentStep', 'unknown'),
            'redirect_url': data.get('redirectUrl'),
            'status_code': status,
            'data': data
        }

    def _upload_document(self, teacher_data: Dict, doc_type: str = "id_card") -> Dict:
        """Upload document and complete the step"""
        logger.info(f"📄 Generating {doc_type} document...")
        
        try:
            # Create shared data to ensure consistency
            from .img_generator import TeacherDocumentData
            
            shared_data = TeacherDocumentData(
                teacher_data['first_name'], 
                teacher_data['last_name'],
                school_name=teacher_data.get('school_name'),
                school_template=teacher_data.get('district_template'),
                position=teacher_data.get('position'),
                hire_date=teacher_data.get('hire_date'),
                employee_id=teacher_data.get('employee_id'),
                annual_salary=teacher_data.get('annual_salary'),
                salary_step=teacher_data.get('salary_step'),
                department=teacher_data.get('department'),
                pension_number=teacher_data.get('pension_number'),
            )
            
            # Generate document
            png_data = generate_teacher_png(
                teacher_data['first_name'],
                teacher_data['last_name'],
                teacher_data['school_name'],
                doc_type=doc_type,
                shared_data=shared_data,
                school_template=teacher_data.get('district_template')
            )
        except Exception as e:
            logger.error(f"Doc gen error: {e}")
            raise
            
        png_size = len(png_data)
        logger.info(f"✓ Document generated: {png_size/1024:.2f} KB")

        # Request upload URL
        doc_body = {
            'files': [{
                'fileName': 'teacher_verification.png',
                'mimeType': 'image/png',
                'fileSize': png_size
            }]
        }
        doc_data, doc_status = self._sheerid_request(
            'POST',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/docUpload",
            doc_body
        )

        if doc_status != 200:
            raise Exception(f"docUpload failed ({doc_status}): {doc_data}")

        documents = doc_data.get('documents') or []
        if not documents:
            raise Exception(f"No upload URL returned: {doc_data}")

        upload_url = documents[0]['uploadUrl']
        logger.info("✓ Got S3 upload URL")

        # Upload to S3
        if not self._upload_to_s3(upload_url, png_data, 'image/png'):
            raise Exception("S3 upload failed")
        logger.info("✓ Uploaded to S3")

        # Complete upload
        complete_data, _ = self._sheerid_request(
            'POST',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/completeDocUpload"
        )
        logger.info(f"✓ Complete: currentStep={complete_data.get('currentStep')}")

        return complete_data

    def _poll_for_result(self) -> Dict:
        """
        Poll SheerID for verification result with progressive intervals.
        
        Check schedule:
        - 15 seconds after submit
        - 30 seconds after submit
        - Then every 3 minutes (up to 15 minutes total)
        """
        # Progressive check intervals in seconds
        check_intervals = [15, 15, 180, 180, 180, 180, 180]  # 15s, 30s total, then 3min x5
        
        logger.info("⏳ Starting status polling (15s, 30s, then every 3min)...")
        
        total_time = 0
        for i, interval in enumerate(check_intervals):
            time.sleep(interval)
            total_time += interval
            
            status = self.check_status()
            current_step = status['current_step']
            data = status.get('data', {})
            redirect_url = status.get('redirect_url')
            
            logger.info(f"Check {i+1}: currentStep={current_step} (after {total_time}s)")
            
            if current_step == 'success':
                logger.info("✅ APPROVED!")
                return {
                    'approved': True, 
                    'status': status,
                    'redirect_url': redirect_url
                }
            
            elif current_step in ['rejected', 'error']:
                # Capture rejection error message
                error_ids = data.get('errorIds', [])
                rejection_reasons = data.get('rejectionReasons', [])
                system_error = data.get('systemErrorMessage', '')
                
                error_message = ""
                if error_ids:
                    error_message = ', '.join(error_ids)
                elif rejection_reasons:
                    error_message = ', '.join(rejection_reasons)
                elif system_error:
                    error_message = system_error
                else:
                    error_message = f"Status: {current_step}"
                
                logger.info(f"❌ REJECTED: {error_message}")
                return {
                    'approved': False, 
                    'status': status,
                    'error_message': error_message,
                    'redirect_url': redirect_url
                }
            
            elif current_step == 'docUpload':
                # Needs document again (previous rejected?)
                logger.info("⚠️ docUpload required again")
                return {
                    'approved': False,
                    'status': status,
                    'error_message': 'Document rejected, need to reupload',
                    'needs_reupload': True
                }
            
            # pending or reviewing - continue polling
            logger.info(f"⏳ Still {current_step}...")
        
        # Timeout - still pending after all checks
        logger.warning("⏳ Timeout - still pending after max checks")
        return {
            'approved': None, 
            'status': status, 
            'timeout': True,
            'error_message': 'Timeout waiting for review (15+ minutes)'
        }

    def verify_with_retry(self, auto_retry: bool = True,
                          doc_type: DocumentType = "id_card",
                          custom_email: str = None) -> Dict:
        """
        Full verification flow with document retry.
        
        NOTE: Once form is submitted, teacher info is locked to verification ID.
        We can only retry with different DOCUMENTS, not different profiles.
        For different profile, need a NEW verification ID (new SheerID link).
        
        Args:
            auto_retry: If True, wait for result and retry document if rejected
            doc_type: Document type for first attempt ("id_card" recommended)
            custom_email: Optional user-provided email (receives SheerID confirmation)
        """
        # Get single teacher profile for this verification
        # Use district template distribution (randomly pick one)
        district_template = random.choice(["nyc_doe", "miami_dade", "springfield_high"])
        teacher = generate_teacher_info(district=district_template)
        
        # Use custom email if provided
        email = custom_email if custom_email else teacher['email']
        
        # Extract fields
        first_name = teacher['first_name']
        last_name = teacher['last_name']
        birth_date = teacher['birth_date']
        school_name = teacher['school_name']
        school_id = teacher.get('school_id', DEFAULT_SCHOOL_ID)
        
        # Build enriched teacher_data for document generation
        teacher_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'birth_date': birth_date,
            'school_name': school_name,
            'district_template': district_template,
            'position': teacher.get('position'),
            'hire_date': teacher.get('hire_date'),
            'department': teacher.get('department'),
            'employee_id': teacher.get('employee_id'),
            'annual_salary': teacher.get('annual_salary'),
            'salary_step': teacher.get('salary_step'),
            'pension_number': teacher.get('pension_number'),
        }
        
        # Lookup school info for SheerID API
        school = SCHOOLS.get(str(school_id), SCHOOLS[DEFAULT_SCHOOL_ID])
        
        teacher_info = {
            'name': f"{first_name} {last_name}",
            'email': email,
            'birth_date': birth_date,
            'school': school_name
        }
        
        logger.info(f"\n{'='*50}")
        logger.info(f"K12 VERIFICATION")
        logger.info(f"Teacher: {first_name} {last_name}")
        logger.info(f"School: {school_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = self._single_verify_attempt(
                first_name, last_name, email, birth_date, school, 
                doc_type, teacher_info, auto_retry,
                teacher_data=teacher_data  # Pass full data
            )
            return result
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {
                'success': False,
                'message': str(e),
                'verification_id': self.verification_id,
                'teacher_info': teacher_info
            }

    def _single_verify_attempt(self, first_name: str, last_name: str,
                               email: str, birth_date: str, school: Dict,
                               doc_type: str, teacher_info: Dict,
                               auto_retry: bool, teacher_data: Dict) -> Dict:
        """Execute a single verification attempt"""
        
        logger.info(f"Teacher: {first_name} {last_name}")
        logger.info(f"Email: {email}")
        logger.info(f"School: {school['name']}")

        # Step 1: Submit form
        form_delay = random.uniform(3.0, 6.0)
        logger.info(f"⏳ Waiting {form_delay:.1f}s...")
        time.sleep(form_delay)

        logger.info("Step 1: Submitting form...")
        step1_body = {
            'firstName': first_name,
            'lastName': last_name,
            'birthDate': birth_date,
            'email': email,
            'phoneNumber': '',
            'organization': {
                'id': school['id'],
                'idExtended': school['idExtended'],
                'name': school['name']
            },
            'deviceFingerprintHash': self.device_fingerprint,
            'locale': 'en-US',
            'metadata': {
                'marketConsentValue': False,
                'refererUrl': f"{SHEERID_BASE_URL}/verify/{PROGRAM_ID}/?verificationId={self.verification_id}",
                'verificationId': self.verification_id,
                'submissionOptIn': 'By submitting...'
            }
        }

        step1_data, step1_status = self._sheerid_request(
            'POST',
            f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/collectTeacherPersonalInfo",
            step1_body
        )

        if step1_status == 404:
            raise Exception("Verification ID expired")
        if step1_status != 200:
            raise Exception(f"Form submit failed: {step1_data}")

        current_step = step1_data.get('currentStep', 'unknown')
        redirect_url = step1_data.get('redirectUrl')
        logger.info(f"✓ Form submitted: currentStep={current_step}")

        # Step 2: Skip SSO if needed
        if current_step == 'sso':
            logger.info("Step 2: Skipping SSO...")
            sso_data, _ = self._sheerid_request(
                'DELETE',
                f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/sso"
            )
            current_step = sso_data.get('currentStep', current_step)
            redirect_url = sso_data.get('redirectUrl') or redirect_url

        # Check result
        if current_step == 'success':
            logger.info("✅ SUCCESS! No document required.")
            return {
                'success': True,
                'pending': False,
                'message': 'Verification successful!',
                'current_step': 'success',
                'verification_id': self.verification_id,
                'redirect_url': redirect_url,
                'teacher_info': teacher_info
            }

        if current_step != 'docUpload':
            logger.info(f"Unexpected step: {current_step}")
            return {
                'success': True,
                'pending': True,
                'current_step': current_step,
                'verification_id': self.verification_id,
                'redirect_url': redirect_url,
                'teacher_info': teacher_info
            }

        # Step 3: Upload document
        school_name = school.get('name', 'Unknown School')
        
        upload_delay = random.uniform(2.0, 4.0)
        logger.info(f"⏳ Waiting {upload_delay:.1f}s before upload...")
        time.sleep(upload_delay)

        complete_data = self._upload_document(teacher_data, doc_type)
        current_step = complete_data.get('currentStep', 'pending')
        redirect_url = complete_data.get('redirectUrl') or redirect_url

        if current_step == 'success':
            logger.info("✅ SUCCESS after document upload!")
            return {
                'success': True,
                'pending': False,
                'message': 'Verification successful!',
                'current_step': 'success',
                'verification_id': self.verification_id,
                'redirect_url': redirect_url,
                'teacher_info': teacher_info
            }

        # Step 4: Poll for result
        if not auto_retry:
            return {
                'success': True,
                'pending': True,
                'message': 'Document submitted, awaiting review',
                'current_step': current_step,
                'verification_id': self.verification_id,
                'redirect_url': redirect_url,
                'teacher_info': teacher_info
            }

        poll_result = self._poll_for_result()
        
        if poll_result.get('approved'):
            final_url = poll_result['status'].get('redirect_url')
            logger.info("✅ APPROVED!")
            return {
                'success': True,
                'pending': False,
                'message': 'Verification approved!',
                'current_step': 'success',
                'verification_id': self.verification_id,
                'redirect_url': final_url,
                'teacher_info': teacher_info
            }

        if poll_result.get('timeout'):
            return {
                'success': True,
                'pending': True,
                'timeout': True,
                'message': 'Still pending after max wait time',
                'verification_id': self.verification_id,
                'teacher_info': teacher_info
            }

        # Step 5: Rejected - get error message and try blank image trick
        error_message = poll_result.get('error_message', 'Document rejected')
        logger.info(f"❌ REJECTED: {error_message}")
        logger.info("Trying blank image trick...")
        
        for blank_attempt in range(MAX_BLANK_RETRIES):
            logger.info(f"Blank image attempt {blank_attempt + 1}/{MAX_BLANK_RETRIES}")
            time.sleep(5)
            
            try:
                self._upload_document(teacher_data, doc_type="blank")
                time.sleep(3)
            except Exception as e:
                logger.info(f"Blank upload {blank_attempt + 1}: {e}")
        
        # Mark as rejected for retry with different profile
        return {
            'success': False,
            'rejected': True,
            'message': f'Rejected: {error_message}',
            'error_message': error_message,
            'verification_id': self.verification_id,
            'teacher_info': teacher_info
        }

    # Legacy method for compatibility
    def verify(self, first_name: str = None, last_name: str = None,
               email: str = None, birth_date: str = None,
               school_id: str = None, doc_type: DocumentType = "id_card",
               auto_retry: bool = False,
               hcaptcha_token: str = None, turnstile_token: str = None,
               custom_email: str = None) -> Dict:
        """
        Legacy verify method - wraps verify_with_retry
        
        Args:
            custom_email: Optional user-provided email for SheerID confirmation
        """
        if auto_retry:
            return self.verify_with_retry(auto_retry=True, doc_type=doc_type, custom_email=custom_email)
        
        # Original single-attempt behavior
        if not first_name or not last_name:
            name = NameGenerator.generate()
            first_name = name['first_name']
            last_name = name['last_name']

        school_id = school_id or DEFAULT_SCHOOL_ID
        school = SCHOOLS[school_id]

        if not email:
            email = generate_email()
        if not birth_date:
            birth_date = generate_birth_date()

        teacher_info = {
            'name': f"{first_name} {last_name}",
            'email': email,
            'birth_date': birth_date,
            'school': school['name']
        }

        try:
            return self._single_verify_attempt(
                first_name, last_name, email, birth_date, school,
                doc_type, teacher_info, auto_retry=False,
                teacher_data={
                     'first_name': first_name,
                     'last_name': last_name,
                     'email': email,
                     'birth_date': birth_date,
                     'school_name': school['name'],
                     'district_template': 'nyc_doe', # Fallback default
                     'position': 'Teacher',
                     'hire_date': '2020-08-20'
                }
            )
        except Exception as e:
            return {
                'success': False,
                'message': str(e),
                'verification_id': self.verification_id,
                'teacher_info': teacher_info
            }
