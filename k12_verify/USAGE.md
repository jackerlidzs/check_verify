# K12 Verify - Hướng Dẫn Sử Dụng Chi Tiết

## Mục Lục
1. [Giới Thiệu](#giới-thiệu)
2. [Cài Đặt](#cài-đặt)
3. [Cấu Hình](#cấu-hình)
4. [Sử Dụng Web UI](#sử-dụng-web-ui)
5. [API Reference](#api-reference)
6. [Database](#database)
7. [Deploy lên VPS](#deploy-lên-vps)
8. [Troubleshooting](#troubleshooting)

---

## Giới Thiệu

K12 Verify là công cụ verification teacher K-12 qua SheerID, hỗ trợ:
- **3 School Districts**: NYC DOE, Miami-Dade, Springfield
- **5 Document Types**: Payslip, ID Card, HR System, Verification Letter, Offer Letter
- **Web UI**: Giao diện 2 cột với live log
- **REST API**: Integration với các hệ thống khác
- **SQLite Database**: Lưu trữ teacher data

---

## Cài Đặt

### 1. Clone Project
```bash
git clone <repository>
cd k12_verify
```

### 2. Cài Dependencies
```bash
pip install -r requirements.txt
```

### 3. Cài Playwright Browser
```bash
playwright install chromium
```

### 4. Chạy Server
```bash
python run.py
```

Server sẽ chạy tại: **http://localhost:8000**

---

## Cấu Hình

### Environment Variables (.env)
```bash
# Copy từ template
cp .env.example .env

# Chỉnh sửa
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./data/k12_verify.db
PLAYWRIGHT_HEADLESS=true
LOG_LEVEL=INFO
```

### Proxy (Optional)
```bash
PROXY_URL=socks5://127.0.0.1:1080
```

---

## Sử Dụng Web UI

### Bước 1: Mở Browser
Truy cập: **http://localhost:8000**

### Bước 2: Lấy Cookies từ Chrome
1. Cài extension **EditThisCookie**: [Chrome Web Store](https://chrome.google.com/webstore/detail/editthiscookie)
2. Truy cập trang SheerID verification
3. Hoàn thành captcha (không cần điền form)
4. Click icon EditThisCookie → **Export** → Copy JSON

### Bước 3: Paste Cookies
Paste cookies JSON vào ô textarea trên Web UI

### Bước 4: Start Verification
Click **▶ Start Verification** và theo dõi progress

### Kết quả:
- ✅ **Approved**: Verification thành công
- ❌ **Rejected**: Document bị từ chối
- ⏳ **Pending**: Đang chờ review

---

## API Reference

### Base URL
```
http://localhost:8000/api
```

### Endpoints

#### 1. Start Verification
```http
POST /api/verify
Content-Type: application/json

{
  "cookies": "[{\"name\":\"sid-verificationId\",\"value\":\"...\"}]"
}
```

**Response:**
```json
{
  "task_id": "a1b2c3d4",
  "status": "running",
  "message": "Verification started for Jorge Chicuri"
}
```

#### 2. Check Status
```http
GET /api/status/{task_id}
```

**Response:**
```json
{
  "task_id": "a1b2c3d4",
  "step": 5,
  "total_steps": 7,
  "status": "running",
  "current_action": "Uploading document...",
  "logs": ["[Step 1/7] Initialize...", "..."]
}
```

#### 3. List Teachers
```http
GET /api/teachers?district=miami_dade&limit=50
```

#### 4. Get Stats
```http
GET /api/stats
```

#### 5. WebSocket (Real-time Log)
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/verify/a1b2c3d4');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.message);
};
```

---

## Database

### Migrate Teacher Data
```bash
python -m app.db.migrate
```

### Models

**Teacher:**
- id, first_name, last_name, email
- school_name, district, employee_id
- position, department, annual_salary

**Verification:**
- id, teacher_id, status, document_type
- verification_id, redirect_url
- started_at, completed_at

---

## Deploy lên VPS

### Option 1: Docker (Recommended)
```bash
# Upload project
scp -r k12_verify/ user@vps:/home/user/

# SSH to VPS
ssh user@vps
cd k12_verify

# Build & Run
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Option 2: Manual
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium --with-deps

# Run with gunicorn
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

### Nginx Reverse Proxy (HTTPS)
```nginx
server {
    listen 443 ssl;
    server_name verify.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## Troubleshooting

### 1. "No module named 'playwright'"
```bash
pip install playwright
playwright install chromium
```

### 2. "Browser executable not found"
```bash
playwright install chromium --with-deps
```

### 3. "Port already in use"
```bash
# Thay đổi port
PORT=8001 python run.py
```

### 4. Database locked
```bash
# Stop all processes
# Delete database and recreate
rm data/k12_verify.db
python -m app.db.migrate
```

### 5. Cookies expired
- Cookies SheerID hết hạn sau ~30 phút
- Cần lấy cookies mới từ browser

---

## Cấu Trúc Project

```
k12_verify/
├── run.py              # Entry point
├── requirements.txt    # Dependencies
├── Dockerfile          # Docker build
├── docker-compose.yml  # Docker Compose
│
├── app/
│   ├── main.py         # FastAPI app
│   ├── config.py       # Settings
│   ├── api/            # REST API
│   ├── core/           # Business logic
│   ├── db/             # SQLite
│   └── templates/      # Web UI
│
├── doc_templates/      # Document templates
│   ├── nyc_doe/
│   ├── miami_dade/
│   └── springfield_high/
│
└── data/
    └── k12_verify.db
```

---

## Support

Issues? Check logs:
```bash
docker-compose logs k12-verify
# or
python run.py 2>&1 | tee app.log
```
