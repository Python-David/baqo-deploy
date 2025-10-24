# Baqo 🚀

**Baqo** is a secure, extensible **bi-directional webhook relay service** — handling both **inbound** webhooks from third-party providers and **outbound** dispatch events to your own systems or partner APIs.

---

## ⚡ Quickstart

Follow these steps to get Baqo running locally with Docker:

### 1. Clone the Deploy Folder

```bash
git clone https://github.com/YOUR_ORG_OR_USERNAME/baqo-deploy.git
cd baqo-deploy
```

This is the standalone deployment repo. It includes Docker setup and configuration.

### 2. Set Up Environment Variables

Copy the example `.env` file and fill in required values:

```bash
cp .env.example .env
```

Set secrets like `POSTGRES_USER`, `STRIPE_SECRET`, etc.

### 3. Configure Sources (Inbound)

Edit `config/source_verification.yaml` to define your webhook sources:

```yaml
sources:
  stripe:
    type: stripe
    secret: ${STRIPE_SECRET}
    event_id_path: id
    handler_url: http://host.docker.internal:9000/
    verify: true
```

### 3b. Configure Destinations (Outbound)

Baqo can also forward or dispatch events to external systems.  
Define outbound destinations in the same YAML file:

```yaml
destinations:
  meetball_success:
    type: none
    handler_url: http://host.docker.internal:9003/success
    verify: false
```

You can then POST to:
```
POST /dispatch/meetball_success
```
to trigger an outbound delivery.

### 4. Build and Run Baqo Locally

Once your `.env` and YAML config are set up, run:

```bash
docker compose up --build
```

This will:
- Start Postgres, Redis, the Baqo app, and Celery worker
- Run migrations automatically
- Start accepting webhooks at `http://localhost:8000/webhooks/{source}`
- Start dispatching outbound events at `http://localhost:8000/dispatch/{destination}`

### 5. Test It

Inbound test:
```bash
curl -X POST http://localhost:8000/webhooks/stripe   -H "Content-Type: application/json"   -H "stripe-signature: your-generated-signature"   -d '{"id": "evt_test_001", "data": {"object": {"id": "pi_001"}}}'
```

Outbound test:
```bash
curl -X POST http://localhost:8000/dispatch/meetball_success   -H "X-BAQO-KEY: secret123"   -H "Content-Type: application/json"   -d '{"event": "user.checkin", "data": {"id": 42}}'
```

---

## 🚀 How Baqo Works

### Inbound Flow (Receive)

```plaintext
+-------------+       +--------+        +-------------+        +--------------+       +------------------+
| 3rd-party   |  -->  |  Baqo  |  -->   |  Postgres    |  -->   |  Celery      |  -->  | Your App Handler |
| service     |       |  API   |        | (Event Log)  |        | Worker Queue |       | (HTTP Receiver)  |
+-------------+       +--------+        +-------------+        +--------------+       +------------------+
       |                  |                    |                      |                         |
       | POST /webhooks   | verify signature   | log + deduplicate    | enqueue delivery        | POST payload
```

### Outbound Flow (Dispatch)

```plaintext
+-----------+       +--------+        +-------------+        +--------------+        +-------------------+
| Your App  |  -->  |  Baqo  |  -->   |  Postgres    |  -->   |  Celery      |  -->  | External Endpoint |
| (Client)  |       |  API   |        | (Event Log)  |        | Worker Queue |       | (Receiver System) |
+-----------+       +--------+        +-------------+        +--------------+        +-------------------+
   |                  |                    |                      |                         |
   | POST /dispatch   | create event       | log event            | enqueue delivery        | POST payload
```

---

## 🧩 What Baqo Provides

- ✅ **Webhook Verification** — HMAC or custom plugin-based verification  
- 🔁 **Retry Logic** — Smart backoff for transient errors (Celery-powered)  
- 🧱 **Deduplication** — Prevent reprocessing via event_id  
- 🔒 **API Key Protection** — Secure outbound endpoints  
- 📜 **Event Logging & Observability** — All attempts logged in Postgres  
- ⚙️ **Extensible** — Add new verification or delivery strategies easily

---

## ⚙️ Configuration

Baqo uses a YAML file mounted at `/app/config/source_verification.yaml`.

### Example

```yaml
sources:
  stripe:
    type: stripe
    secret: ${STRIPE_SECRET}
    event_id_path: id
    handler_url: http://your-backend.com/stripe-events
    verify: true

  paystack:
    type: paystack
    secret: ${PAYSTACK_SECRET}
    event_id_path: data.id
    handler_url: http://your-backend.com/paystack-handler
    verify: true

destinations:
  meetball_success:
    type: none
    handler_url: http://host.docker.internal:9003/success
    verify: false
```

### Field Reference

| Field | Description |
|--------|-------------|
| `type` | Plugin type (for verification or categorization) |
| `secret` | Secret key for signature verification (inbound only) |
| `event_id_path` | JSON path to event ID for deduplication |
| `handler_url` | Target URL for forwarding or dispatch |
| `verify` | Whether to verify TLS/SSL (disable for trusted LANs) |

---

## 🧾 .env Configuration Reference

| Variable | Purpose |
|-----------|----------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Database credentials |
| `CELERY_BROKER_URL` | Redis broker for Celery |
| `CELERY_RESULT_BACKEND` | Redis backend for Celery |
| `CELERY_MAX_RETRIES` | Max delivery retries |
| `CELERY_BACKOFF_BASE_DELAY` | Base delay for retry backoff |
| `BAQO_API_KEY` | Protects outbound `/dispatch/*` endpoints |
| `LOG_LEVEL`, `LOG_FORMAT`, `LOG_DATE_FORMAT` | Logging settings |
| `RUNNING_IN_DOCKER` | Should remain `true` for containerized deployments |

---

## 🧠 Inbound vs Outbound

| Direction | Endpoint | Verification | Deduplication | Typical Use |
|------------|-----------|--------------|----------------|--------------|
| **Inbound** | `/webhooks/{source}` | Optional (Stripe, Paystack, etc.) | ✅ Yes | Receive events from third parties |
| **Outbound** | `/dispatch/{destination}` | API Key | ❌ No | Send events to partner systems |

---

## 🪵 Observability

Each event record includes:

- `last_status_code` — last HTTP response code received  
- `last_response_excerpt` — truncated text from the last response  
- `last_attempt_at` — last delivery attempt timestamp  
- `last_error` — latest known failure reason  

This allows you to monitor event delivery health and debug failures easily.

---

## 🔐 Custom Verification

You can add your own signature logic via `custom_verifications/`:

```python
# app/custom_verifications/mycompany.py
VERIFICATION_TYPE = "mycompany_signature"

from starlette.datastructures import Headers

async def verify_signature(secret: str, headers: Headers, body_str: str):
    signature = headers.get("x-mycompany-signature")
    if not signature or signature != secret:
        raise Exception("Invalid MyCompany signature")
```

Then reference it in YAML:

```yaml
sources:
  mycompany:
    type: mycompany_signature
    secret: ${MYCOMPANY_SECRET}
    event_id_path: id
    handler_url: http://your-app.com/handler
    verify: true
```

---

## 🧩 Example Outbound Integration

Send a dispatch event manually:

```bash
curl -X POST http://localhost:8000/dispatch/meetball_success   -H "X-BAQO-KEY: secret123"   -H "Content-Type: application/json"   -d '{"event": "order.created", "data": {"id": "12345"}}'
```

---

## 📜 Logs & Monitoring

Follow app logs:
```bash
docker compose logs -f app
```

Follow worker logs:
```bash
docker compose logs -f worker
```

Query events directly in Postgres to view retry history and results.

---

**Baqo v0.2.0 — now with full outbound dispatching, improved observability, and smarter retries!** 🌀
