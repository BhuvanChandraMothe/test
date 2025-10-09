## 🚀 SAP OData Connector API - Complete Guide

**Architecture with SQLite Persistence**

This API uses a **3-step workflow** with persistent storage:

1. **Create Config** → Get `config_id` (stored in SQLite)
2. **Create Session** → Get `session_id` (initialized connector)
3. **Execute Query** → Get `job_id` (background job)
4. **Check Job** → Get results

---

## 📦 Installation

```bash
pip install fastapi uvicorn
```

---

## 🚀 Start the API

```bash
uvicorn api.main:app --reload --port 8000
```

API will be available at: **http://localhost:8000**

---

## 📋 Complete Workflow Example

### Step 1: Create Configuration

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/configs" \
  -H "Content-Type: application/json" \
  -d '{
    "sap_server": "sapes5.sapdevcenter.com",
    "sap_port": 443,
    "sap_module": "ES5",
    "username": "P2010682507",
    "password": "Bhuvan@2001"
  }'
```

**Response:**
```json
{
  "config_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "created",
  "message": "Configuration saved successfully",
  "next_step": "POST /api/v1/sessions with config_id=a1b2c3d4..."
}
```

**✅ Save the `config_id`!**

---

### Step 2: Initialize Session

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

**Response:**
```json
{
  "session_id": "session-12345-abcde",
  "config_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "initialized",
  "message": "Connector initialized successfully",
  "service_info": {
    "total_entities": 9,
    "total_records": 2074
  },
  "next_step": "POST /api/v1/query with session_id=session-12345..."
}
```

**✅ Save the `session_id`!**

---

### Step 3: Execute Query

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-12345-abcde",
    "entity_name": "Products",
    "filter_condition": "Price gt 100",
    "order_by": "Price desc",
    "record_limit": 50
  }'
```

**Response:**
```json
{
  "job_id": "job-98765-xyz",
  "session_id": "session-12345-abcde",
  "status": "pending",
  "message": "Query job created successfully",
  "next_step": "GET /api/v1/jobs/job-98765-xyz to check status"
}
```

**✅ Save the `job_id`!**

---

### Step 4: Check Job Status

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/job-98765-xyz"
```

**Response (Running):**
```json
{
  "job_id": "job-98765-xyz",
  "session_id": "session-12345-abcde",
  "status": "running",
  "query_params": {...},
  "created_at": "2025-10-09T15:30:00"
}
```

**Response (Completed):**
```json
{
  "job_id": "job-98765-xyz",
  "session_id": "session-12345-abcde",
  "status": "completed",
  "created_at": "2025-10-09T15:30:00",
  "completed_at": "2025-10-09T15:30:15",
  "result_path": "./api_data/results/session-12345/job-98765-xyz.json",
  "download_url": "/api/v1/jobs/job-98765-xyz/download"
}
```

---

### Step 5: Download Results

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/job-98765-xyz/download" \
  -o results.json
```

**Response:**
```json
{
  "execution_stats": {
    "records_processed": 50,
    "duration_seconds": 3.24,
    "entities_processed": 1
  },
  "data": {
    "Products": {
      "records": [...]
    }
  }
}
```

---

## 📊 All API Endpoints

### Configuration Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/configs` | Create configuration |
| GET | `/api/v1/configs` | List all configurations |
| GET | `/api/v1/configs/{config_id}` | Get specific configuration |
| DELETE | `/api/v1/configs/{config_id}` | Delete configuration |

### Session Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions` | Initialize session |
| GET | `/api/v1/sessions` | List all sessions |
| GET | `/api/v1/sessions/{session_id}` | Get specific session |
| GET | `/api/v1/sessions/{session_id}/entities` | List entities in session |
| DELETE | `/api/v1/sessions/{session_id}` | Delete session |

### Query Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/query` | Execute query (background) |
| GET | `/api/v1/jobs` | List all jobs |
| GET | `/api/v1/jobs/{job_id}` | Get job status |
| GET | `/api/v1/jobs/{job_id}/download` | Download results |
| DELETE | `/api/v1/jobs/{job_id}` | Delete job |

### Utility Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

---

## 🐍 Python Client Example

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# Step 1: Create Config
config_response = requests.post(
    f"{BASE_URL}/api/v1/configs",
    json={
        "sap_server": "sapes5.sapdevcenter.com",
        "sap_port": 443,
        "sap_module": "ES5",
        "username": "P2010682507",
        "password": "Bhuvan@2001"
    }
)
config_id = config_response.json()["config_id"]
print(f"✓ Config created: {config_id}")

# Step 2: Initialize Session
session_response = requests.post(
    f"{BASE_URL}/api/v1/sessions",
    json={"config_id": config_id}
)
session_id = session_response.json()["session_id"]
print(f"✓ Session initialized: {session_id}")

# Step 3: List Entities
entities_response = requests.get(
    f"{BASE_URL}/api/v1/sessions/{session_id}/entities"
)
print(f"✓ Total entities: {entities_response.json()['total_entities']}")

# Step 4: Execute Query
query_response = requests.post(
    f"{BASE_URL}/api/v1/query",
    json={
        "session_id": session_id,
        "entity_name": "Products",
        "filter_condition": "Price gt 50",
        "order_by": "Price desc",
        "record_limit": 10
    }
)
job_id = query_response.json()["job_id"]
print(f"✓ Job started: {job_id}")

# Step 5: Wait for completion
while True:
    status_response = requests.get(f"{BASE_URL}/api/v1/jobs/{job_id}")
    status = status_response.json()["status"]
    print(f"  Status: {status}")
    
    if status == "completed":
        break
    elif status == "failed":
        print("❌ Job failed!")
        break
    
    time.sleep(2)

# Step 6: Download results
results_response = requests.get(
    f"{BASE_URL}/api/v1/jobs/{job_id}/download"
)
results = results_response.json()
print(f"✓ Records: {results['execution_stats']['records_processed']}")

# Step 7: Cleanup
requests.delete(f"{BASE_URL}/api/v1/sessions/{session_id}")
print("✓ Session deleted")
```

---

## 💾 Database Structure

The API uses **SQLite** with 3 tables:

### 1. configurations
Stores connection configurations
- `config_id` (PRIMARY KEY)
- `service_url`, `sap_server`, `sap_port`, `sap_module`
- `username`, `password` (encrypted in production)
- `created_at`, `updated_at`

### 2. sessions
Stores initialized connector sessions
- `session_id` (PRIMARY KEY)
- `config_id` (FOREIGN KEY)
- `status`, `service_info`
- `created_at`, `last_used_at`

### 3. query_jobs
Stores query execution jobs
- `job_id` (PRIMARY KEY)
- `session_id` (FOREIGN KEY)
- `query_params`, `status`, `result_path`, `error`
- `created_at`, `completed_at`

**Database Location:** `./api_data/connector.db`

---

## 🔍 Query Parameters Reference

### Configuration Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `service_url` | string | No* | Full OData service URL |
| `sap_server` | string | No* | SAP server hostname |
| `sap_port` | int | No | SAP server port (default: 443) |
| `sap_module` | string | No | SAP module (e.g., ES5) |
| `use_https` | bool | No | Use HTTPS (default: true) |
| `username` | string | No | Username |
| `password` | string | No | Password |
| `output_directory` | string | No | Output directory |
| `timeout` | int | No | Timeout (default: 60) |

*Either `service_url` OR (`sap_server` + `sap_module`) required

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session ID |
| `entity_name` | string | No* | Single entity |
| `selected_entities` | array | No* | Multiple entities |
| `filter_condition` | string | No | $filter condition |
| `select_fields` | string | No | $select fields |
| `expand_relations` | string | No | $expand relations |
| `order_by` | string | No | $orderby clause |
| `record_limit` | int | No | Max records |
| `batch_size` | int | No | Batch size (default: 1000) |
| `max_workers` | int | No | Workers (default: 5) |

*Either `entity_name` OR `selected_entities` required

---

## 🎯 Advanced Examples

### Example 1: Reuse Configuration

```python
# Create config once
config_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

# Create multiple sessions from same config
session1 = requests.post(f"{BASE_URL}/api/v1/sessions", json={"config_id": config_id})
session2 = requests.post(f"{BASE_URL}/api/v1/sessions", json={"config_id": config_id})

# Use different sessions for parallel queries
```

### Example 2: Multiple Queries in Parallel

```python
# Start multiple jobs
job_ids = []
for entity in ["Products", "Suppliers", "Reviews"]:
    response = requests.post(
        f"{BASE_URL}/api/v1/query",
        json={
            "session_id": session_id,
            "entity_name": entity
        }
    )
    job_ids.append(response.json()["job_id"])

# Wait for all to complete
for job_id in job_ids:
    while True:
        status = requests.get(f"{BASE_URL}/api/v1/jobs/{job_id}").json()
        if status["status"] in ["completed", "failed"]:
            break
        time.sleep(1)
```

### Example 3: List All Active Sessions

```python
sessions = requests.get(f"{BASE_URL}/api/v1/sessions").json()
print(f"Active sessions: {sessions['total']}")
for session in sessions['sessions']:
    print(f"  - {session['session_id']}: {session['status']}")
```

---

## 🔒 Security Best Practices

### 1. Environment Variables

```python
import os

config = {
    "username": os.getenv("SAP_USERNAME"),
    "password": os.getenv("SAP_PASSWORD")
}
```

### 2. Add Authentication

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@app.post("/api/v1/configs")
async def create_config(
    config: ConfigCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Validate token
    ...
```

### 3. Encrypt Passwords

```python
from cryptography.fernet import Fernet

# Generate key once
key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt before storing
encrypted_password = cipher.encrypt(password.encode())

# Decrypt when using
password = cipher.decrypt(encrypted_password).decode()
```

---

## 📈 Monitoring

### Check API Health

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-09T15:30:00",
  "database": {
    "total_configs": 5,
    "total_sessions": 3,
    "total_jobs": 12,
    "completed_jobs": 10,
    "running_jobs": 2
  },
  "active_connectors": 3
}
```

---

## 🐛 Troubleshooting

### Issue 1: Session Not Active

**Error:** "Session not active. Please reinitialize."

**Solution:** Create a new session:
```bash
curl -X POST "http://localhost:8000/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"config_id": "your-config-id"}'
```

### Issue 2: Job Stuck in "running"

**Check logs** and restart the API if needed.

### Issue 3: Database Locked

**Solution:** Close other connections or restart API.

---

## 🚀 Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Run:
```bash
docker build -t sap-odata-api .
docker run -p 8000:8000 -v ./api_data:/app/api_data sap-odata-api
```

---

**Your API is ready with persistent SQLite storage! 🎉**
