"""Generate test document first, then use it"""
from app.core.document_gen import generate_teacher_png

SCREENSHOT_DIR = "C:/Users/jacke/.gemini/antigravity/brain/be827772-77bf-4f48-91ad-569cf624d56b"

print("Generating test document...")
image_bytes = generate_teacher_png(
    first_name="John",
    last_name="Smith",
    school_name="Miami Beach Senior High",
    doc_type="payslip"
)

doc_path = f"{SCREENSHOT_DIR}/test_payslip.png"
with open(doc_path, 'wb') as f:
    f.write(image_bytes)
print(f"Document saved: {doc_path}")
