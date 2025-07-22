
# Baqo

**Baqo** is a secure, extensible webhook relay service designed for SaaS teams that want to ingest and process webhooks reliably without building complex verification, de-duplication, and retry logic from scratch.

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

### 3. Configure Sources

Edit `config/source_verification.yaml` to define your webhook sources:

```yaml
sources:
  stripe:
    type: stripe
    secret: ${STRIPE_SECRET}
    event_id_path: id
    handler_url: http://host.docker.internal:9000/  # Your backend URL
    verify: true
```

### 4. Build and Run Baqo Locally

Once your `.env` and YAML config are set up, run:

```bash
docker compose up --build
```

This will:
- Start Postgres, Redis, the Baqo app, and Celery worker
- Run migrations automatically
- Start accepting webhooks at `http://localhost:8000/webhooks/{source}`

### 5. Test it

Send a webhook for testing:

```bash
curl -X POST http://localhost:8000/webhooks/stripe   -H "Content-Type: application/json"   -H "stripe-signature: your-generated-signature"   -d '{"id": "evt_test_001", "data": {"object": {"id": "pi_001"}}}'
```

Check logs:

```bash
docker compose logs -f app
```

---

## 🚀 How Baqo Works

When an external service (e.g. Stripe, Paystack) sends your app a webhook:

```plaintext
+-------------+       +--------+        +-------------+        +--------------+       +------------------+
| 3rd-party   |  -->  |  Baqo  |  -->   |  Postgres    |  -->   |  Celery      |  -->  | Your App Handler |
| service     |       |  API   |        | (Event Log)  |        | Worker Queue |       | (HTTP Receiver)  |
+-------------+       +--------+        +-------------+        +--------------+       +------------------+
       |                  |                    |                      |                         |
       | POST /webhooks   | verify signature   | log + deduplicate    | enqueue delivery        | POST payload
       |----------------->|------------------->|--------------------->|------------------------>| to handler_url
```

---

## 🧩 What Baqo Provides

Baqo offers the following key services out-of-the-box:

- **Webhook Verification**: HMAC or custom logic to verify incoming webhook authenticity
- **Event Deduplication**: Avoid processing the same event multiple times via `event_id_path`
- **Retry Logic**: Events are pushed to your handler URL with retry policies using Celery workers
- **Event Logging**: Every incoming webhook is logged in your Postgres DB
- **Extensible Verification**: Add your own logic for signature verification via simple plugins

---

## ⚙️ Configuration

Configuration is managed via a YAML file, typically mounted into the container as `source_verification.yaml`.

### Example `source_verification.yaml`

```yaml
sources:
  stripe:
    type: stripe
    secret: ${STRIPE_SECRET}
    event_id_path: id
    handler_url: http://your-backend.com/stripe-events
    verify: true

  mycompany:
    type: mycompany_signature
    secret: ${MYCOMPANY_SECRET}
    event_id_path: data.txn_id
    handler_url: http://your-backend.com/mycompany-handler
    verify: true

  open_source:
    type: none
    event_id_path: data.transaction_id
    handler_url: https://example.com/open-handler
    verify: false
```

### Field Explanations

| Field             | Description                                                                 |
|------------------|-----------------------------------------------------------------------------|
| `type`           | The name of the verification plugin to use (e.g. `stripe`, `mycompany_signature`, or `none`) |
| `secret`         | The secret used in the verification process (optional depending on type)     |
| `event_id_path`  | Dot path to the unique ID of the event (used for deduplication)              |
| `handler_url`    | The URL to forward verified events to                                        |
| `verify`         | If false, skips signature verification (trusted sources only)                |

---

## 🧾 .env Configuration Reference

Baqo uses environment variables (typically from a `.env` file) to control key runtime behavior.

| Variable                 | Purpose                                                        |
|--------------------------|----------------------------------------------------------------|
| `POSTGRES_USER`          | Username for the Postgres database                             |
| `POSTGRES_PASSWORD`      | Password for the Postgres database                             |
| `POSTGRES_DB`            | Name of the Postgres database                                  |
| `STRIPE_SECRET`, etc.    | Webhook secrets for each source, referenced in YAML            |
| `CELERY_BROKER_URL`      | URL for Redis broker used by Celery                            |
| `CELERY_RESULT_BACKEND`  | Backend store for Celery task results (also Redis)             |
| `CELERY_MAX_RETRIES`     | Max number of retries for forwarding failed events             |
| `CELERY_BACKOFF_BASE_DELAY` | Base delay (in seconds) before retrying a failed task       |
| `LOG_LEVEL`              | Logging level (DEBUG, INFO, etc.)                              |
| `LOG_FORMAT`             | Format for log messages                                         |
| `LOG_DATE_FORMAT`        | Format for timestamps in logs                                   |
| `SOURCE_VERIFICATION_FILE` | Path to the YAML file with source configuration             |
| `RUNNING_IN_DOCKER`      | Used internally to determine DB host resolution (keep as true) |
| `RUNNING_TESTS_IN_DOCKER`| Same as above, for test containers                              |

---

## 🔐 Custom Verification Logic

You can define your own verification logic by adding Python files to the `custom_verifications/` folder.

Each file must define:

- `VERIFICATION_TYPE`: A string name to reference in the YAML
- `verify_signature(secret, headers, body_str)`: An async def that verifies the request

### Example: `custom_verifications/mycompany.py`

```python
VERIFICATION_TYPE = "mycompany_signature"

from starlette.datastructures import Headers

async def verify_signature(secret: str, headers: Headers, body_str: str):
    signature = headers.get("x-mycompany-signature")
    if not signature:
        raise Exception("Missing MyCompany signature")
    if signature != secret:
        raise Exception("Invalid signature")
```

### Then in your config:

```yaml
sources:
  mycompany:
    type: mycompany_signature
    secret: ${MYCOMPANY_SECRET}
    event_id_path: id
    handler_url: http://your-backend.com/
```

> 📁 This file must be placed in the `custom_verifications/` folder, mounted into the container at `/app/app/custom_verifications/`.

---

## 🔒 Security Note

Baqo supports custom verification plugins written in Python. These plugins are executed at runtime with full access to the container’s environment. They can:
- Access `.env` secrets
- Make external network requests
- Read/write files inside the container

⚠️ Treat custom verification files as trusted code.

### ✅ Best practices:
- Only your team or verified users should modify these files
- Keep the deploy directory secured and version-controlled
- Run Baqo in a container (as provided) to sandbox plugin behavior

---

## 📜 Viewing Logs

Baqo logs all incoming webhook activity and delivery attempts.

### Live Logs (Docker)

```bash
docker compose logs -f app
```

For the Celery worker:

```bash
docker compose logs -f worker
```

### Database Logs

All events are saved to Postgres with fields like:

- source
- event_id
- status
- payload
- handler_url

You can query them directly for audit/debugging.

---

**Need help? Reach out or open an issue. Baqo! 🚀**
