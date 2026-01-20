"""
API Routes for K12 Verify
"""
import uuid
import json
import asyncio
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db import crud
from ..config import DISTRICTS
from .schemas import (
    VerifyRequest, VerifyURLRequest, VerifyResponse, StatusResponse,
    TeacherResponse, StatsResponse, GenerateDocRequest
)

router = APIRouter(prefix="/api", tags=["api"])

# Store active verification tasks
active_tasks = {}


# ============ VERIFICATION ENDPOINTS ============

@router.post("/verify", response_model=VerifyResponse)
async def start_verification(request: VerifyRequest, db: Session = Depends(get_db)):
    """Start a new verification task."""
    task_id = str(uuid.uuid4())[:8]
    
    # Parse cookies to extract verification ID
    try:
        cookies = json.loads(request.cookies)
        verification_id = None
        for cookie in cookies:
            if cookie.get("name") == "sid-verificationId":
                verification_id = cookie.get("value")
                break
        
        if not verification_id:
            raise HTTPException(status_code=400, detail="sid-verificationId cookie not found")
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid cookies JSON format")
    
    # Get random teacher for verification
    district = request.district or "miami_dade"
    teacher = crud.get_random_teacher(db, district=district)
    
    if not teacher:
        raise HTTPException(status_code=404, detail=f"No teachers found for district: {district}")
    
    # Create task
    active_tasks[task_id] = {
        "status": "running",
        "step": 0,
        "logs": [],
        "teacher": {
            "name": f"{teacher.first_name} {teacher.last_name}",
            "email": teacher.email,
            "school": teacher.school_name
        },
        "verification_id": verification_id,
        "started_at": datetime.now().isoformat()
    }
    
    # Start async verification (in background)
    asyncio.create_task(run_verification(task_id, cookies, teacher, db))
    
    return VerifyResponse(
        task_id=task_id,
        status="running",
        message=f"Verification started for {teacher.first_name} {teacher.last_name}"
    )


async def run_verification(task_id: str, cookies: list, teacher, db: Session):
    """Run REAL verification using CookieVerifier with structured step tracking."""
    from ..core.verifier import CookieVerifier, parse_cookie_json
    import re
    
    task = active_tasks[task_id]
    
    # Step definitions for Progress Bar
    STEPS = {
        1: {"name": "Initialize", "action": "Initializing verification..."},
        2: {"name": "Submit teacher info", "action": "Submitting teacher information..."},
        3: {"name": "Skip SSO", "action": "Handling SSO..."},
        4: {"name": "Get upload URL", "action": "Requesting upload URL..."},
        5: {"name": "Upload document", "action": "Uploading document..."},
        6: {"name": "Complete upload", "action": "Completing upload..."},
        7: {"name": "Poll result", "action": "Checking verification status..."},
    }
    
    def add_log(message: str, step: int = None, status: str = "info"):
        """Add log with structured step info."""
        task["logs"].append({
            "message": message,
            "step": step or task.get("step", 0),
            "status": status,  # info, success, error, warning, step
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
    
    def update_step(step_num: int, status: str = "active", detail: str = None):
        """Update current step with status."""
        task["step"] = step_num
        task["step_status"] = status  # active, completed, error, warning
        step_info = STEPS.get(step_num, {})
        msg = f"🔵 Step {step_num}/7: {step_info.get('name', 'Unknown')}"
        if detail:
            msg += f" - {detail}"
        add_log(msg, step_num, "step")
    
    try:
        # Parse cookies to dict format
        cookies_dict = {}
        for cookie in cookies:
            cookies_dict[cookie.get('name')] = cookie.get('value')
        
        # Initial info logs
        add_log(f"📋 Verification ID: {task['verification_id'][:20]}...", status="info")
        add_log(f"👤 Teacher: {teacher.first_name} {teacher.last_name}", status="info")
        add_log(f"🏫 School: {teacher.school_name}", status="info")
        add_log(f"📧 Email: {teacher.email}", status="info")
        
        # Status callback to parse verifier output
        current_step = [1]  # Use list for closure
        
        def status_callback(step_label, message):
            # Parse step number from verifier
            step_match = re.search(r'STEP(\d)', step_label)
            if step_match:
                step_num = int(step_match.group(1))
                current_step[0] = step_num
                task["step"] = step_num
            
            # Detect status from message content
            status = "info"
            if "✅" in message or "completed" in message.lower():
                status = "success"
                task["step_status"] = "completed"
            elif "❌" in message or "error" in message.lower() or "failed" in message.lower():
                status = "error"
                task["step_status"] = "error"
            elif "⚠️" in message or "warning" in message.lower() or "captcha" in message.lower():
                status = "warning"
                task["step_status"] = "warning"
            elif "Step" in message and "/" in message:
                status = "step"
                task["step_status"] = "active"
            
            add_log(message, current_step[0], status)
        
        # Step 1: Initialize
        update_step(1, "active")
        add_log("🚀 Starting SheerID verification...", 1, "info")
        
        # Create verifier with cookies
        verifier = CookieVerifier(
            cookies=cookies_dict,
            custom_email=teacher.email,
            status_callback=status_callback
        )
        
        add_log("✅ Verifier initialized", 1, "success")
        task["step_status"] = "completed"
        
        # Run verification (this calls SheerID API!)
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, verifier.verify)
        
        # Process result
        if result.get('success') or result.get('approved'):
            task["status"] = "success"
            redirect_url = result.get('status', {}).get('redirect_url', 'N/A')
            task["result"] = {
                "approved": True,
                "redirect_url": redirect_url,
                "teacher": task["teacher"]
            }
            update_step(7, "completed")
            add_log("🎉 VERIFICATION APPROVED!", 7, "success")
            add_log(f"🔗 Redirect URL: {redirect_url}", 7, "success")
            
        elif result.get('rejected'):
            task["status"] = "rejected"
            reasons = result.get('rejection_reasons', ['Unknown'])
            task["result"] = {
                "approved": False,
                "rejection_reasons": reasons,
                "teacher": task["teacher"]
            }
            update_step(7, "error", "Document rejected")
            add_log(f"❌ REJECTED: {', '.join(reasons)}", 7, "error")
            
        elif result.get('pending'):
            task["status"] = "success"
            task["result"] = {
                "approved": None,
                "pending": True,
                "teacher": task["teacher"]
            }
            update_step(7, "completed")
            add_log("⏳ Document submitted, pending review", 7, "success")
            
        else:
            task["status"] = "error"
            error_msg = result.get('message', 'Unknown error')
            update_step(task.get("step", 7), "error", error_msg)
            add_log(f"❌ Error: {error_msg}", task.get("step", 7), "error")
        
    except Exception as e:
        task["status"] = "error"
        update_step(task.get("step", 1), "error", str(e))
        add_log(f"❌ Exception: {str(e)}", task.get("step", 1), "error")


# ============ URL-BASED VERIFICATION ============

@router.post("/verify-url", response_model=VerifyResponse)
async def start_url_verification(request: VerifyURLRequest, db: Session = Depends(get_db)):
    """Start verification using SheerID URL only (no cookies needed)."""
    task_id = str(uuid.uuid4())[:8]
    
    # Validate URL
    if not request.url or 'sheerid' not in request.url.lower():
        raise HTTPException(status_code=400, detail="Invalid SheerID URL")
    
    # Create task
    active_tasks[task_id] = {
        "status": "running",
        "step": 0,
        "logs": [],
        "verification_url": request.url,
        "started_at": datetime.now().isoformat()
    }
    
    # Start async verification
    asyncio.create_task(run_url_verification(task_id, request.url, request.email))
    
    return VerifyResponse(
        task_id=task_id,
        status="running",
        message=f"URL verification started"
    )


async def run_url_verification(task_id: str, url: str, custom_email: str = None):
    """Run URL-based verification in background."""
    from ..core.url_verifier import URLVerifier
    
    task = active_tasks[task_id]
    
    def add_log(message: str, step: int = None, status: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        task["logs"].append({
            "time": timestamp,
            "message": message,
            "step": step,
            "status": status
        })
    
    def update_step(step_num: int, status: str = "active", detail: str = None):
        task["step"] = step_num
        task["current_action"] = detail
    
    def status_callback(step_label: str, message: str):
        add_log(f"[{step_label}] {message}")
    
    try:
        add_log("🚀 Starting URL-based verification...")
        update_step(1)
        
        # Create verifier
        verifier = URLVerifier(
            verification_url=url,
            custom_email=custom_email,
            status_callback=status_callback
        )
        
        add_log(f"📋 Verification ID: {verifier.verification_id[:20]}...")
        add_log("✅ Verifier initialized")
        
        # Run verification
        result = await asyncio.get_event_loop().run_in_executor(
            None, verifier.verify
        )
        
        # Handle result
        if result.get('success'):
            task["status"] = "success"
            task["result"] = result
            add_log("✅ VERIFICATION SUCCESSFUL!", 7, "success")
            if result.get('redirectUrl'):
                add_log(f"🔗 Redirect: {result['redirectUrl']}")
        elif result.get('pending'):
            task["status"] = "pending"
            add_log("⏳ Document submitted, pending review", 6, "warning")
        else:
            task["status"] = "error"
            error_msg = result.get('message', 'Verification failed')
            add_log(f"❌ {error_msg}", 7, "error")
        
    except Exception as e:
        task["status"] = "error"
        add_log(f"❌ Error: {str(e)}", 1, "error")

# ============ BROWSER-BASED VERIFICATION - REMOVED ============
# Browser mode removed due to CSS selector instability.
# Use Cookie or URL mode instead - both use stable API calls.
# See: verifier.py (Cookie) and url_verifier.py (URL)


@router.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str):
    """Get verification task status."""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = active_tasks[task_id]
    return StatusResponse(
        task_id=task_id,
        step=task["step"],
        status=task["status"],
        current_action=task["logs"][-1] if task["logs"] else None,
        logs=task["logs"],
        result=task.get("result")
    )


# ============ TEACHER ENDPOINTS ============

@router.get("/teachers", response_model=List[TeacherResponse])
async def list_teachers(
    district: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List teachers from database."""
    teachers = crud.get_teachers(db, district=district, skip=skip, limit=limit)
    return teachers


@router.get("/teachers/{teacher_id}", response_model=TeacherResponse)
async def get_teacher(teacher_id: int, db: Session = Depends(get_db)):
    """Get teacher by ID."""
    teacher = crud.get_teacher(db, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


# ============ STATS ENDPOINT ============

@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    total = crud.count_teachers(db)
    
    districts = {}
    for district_key in DISTRICTS.keys():
        districts[district_key] = crud.count_teachers(db, district=district_key)
    
    return StatsResponse(
        total_teachers=total,
        districts=districts,
        recent_verifications=len(active_tasks),
        success_rate=0.95
    )


# ============ WEBSOCKET FOR LIVE LOGS ============

@router.websocket("/ws/verify/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket for real-time log streaming."""
    await websocket.accept()
    
    if task_id not in active_tasks:
        await websocket.send_json({"error": "Task not found"})
        await websocket.close()
        return
    
    last_log_count = 0
    
    try:
        while True:
            task = active_tasks.get(task_id)
            if not task:
                break
            
            # Send new logs (structured format)
            if len(task["logs"]) > last_log_count:
                new_logs = task["logs"][last_log_count:]
                for log in new_logs:
                    # Log can be dict (structured) or string (legacy)
                    if isinstance(log, dict):
                        await websocket.send_json({
                            "type": "log",
                            "message": log.get("message", ""),
                            "step": log.get("step", task["step"]),
                            "log_status": log.get("status", "info"),  # Log entry status
                            "step_status": task.get("step_status", "active"),  # Step progress status
                            "timestamp": log.get("timestamp", ""),
                            "status": task["status"]  # Overall task status
                        })
                    else:
                        # Legacy string format
                        await websocket.send_json({
                            "type": "log",
                            "message": str(log),
                            "step": task["step"],
                            "log_status": "info",
                            "step_status": task.get("step_status", "active"),
                            "status": task["status"]
                        })
                last_log_count = len(task["logs"])
            
            # Check if done
            if task["status"] in ["success", "error", "rejected"]:
                await websocket.send_json({
                    "type": "complete",
                    "status": task["status"],
                    "step": task["step"],
                    "step_status": task.get("step_status", "completed"),
                    "result": task.get("result")
                })
                break
            
            await asyncio.sleep(0.3)  # Faster updates
            
    except WebSocketDisconnect:
        pass
