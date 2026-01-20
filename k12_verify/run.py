"""
Server runner with Windows subprocess fix for Playwright.
Run this instead of uvicorn directly.
"""
import sys
import asyncio
import os
import signal
import atexit

# CRITICAL: Set Windows event loop policy BEFORE any other imports
if sys.platform == 'win32':
    # Use WindowsProactorEventLoopPolicy for subprocess support
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("[*] Windows Proactor event loop policy set")

# Store server reference for cleanup
_server_process = None

def cleanup():
    """Cleanup function called on exit."""
    global _server_process
    print("\n[*] Shutting down server...")
    if _server_process:
        _server_process.terminate()
    # Kill any remaining python processes on port 8000
    if sys.platform == 'win32':
        os.system('taskkill /F /IM python.exe 2>nul')

def signal_handler(signum, frame):
    """Handle Ctrl+C and other signals."""
    print(f"\n[*] Received signal {signum}, shutting down...")
    cleanup()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Terminate
if sys.platform == 'win32':
    signal.signal(signal.SIGBREAK, signal_handler)  # Windows Ctrl+Break

# Register cleanup on exit
atexit.register(cleanup)

def test_subprocess():
    """Quick test if subprocess is working."""
    import subprocess
    try:
        result = subprocess.run(['python', '--version'], capture_output=True, text=True, timeout=5)
        print(f"[OK] Subprocess test: {result.stdout.strip()}")
        return True
    except Exception as e:
        print(f"[!] Subprocess test failed: {e}")
        return False

if __name__ == "__main__":
    print("[*] K12 Verify Server starting...")
    print("[*] Press Ctrl+C to stop server")
    
    # Test subprocess
    if not test_subprocess():
        print("[!] Subprocess not working, Playwright may fail")
    
    # Change to app directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Import and run uvicorn
    import uvicorn
    
    print("[*] Starting uvicorn on http://localhost:8000 ...")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            workers=1,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n[*] Server stopped by user")
    finally:
        cleanup()
