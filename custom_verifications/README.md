
# Custom Verification Plugins

You can add your own verification logic here by creating Python files in this folder.

## Example

Create a file, e.g., `mycompany.py`:

```python
VERIFICATION_TYPE = "mycompany_signature"

from starlette.datastructures import Headers

async def verify_signature(secret: str, headers: Headers, body_str: str):
    """
    Custom verification logic for MyCompany webhooks.

    Arguments:
    - secret: str → Secret string from YAML config (can be empty).
    - headers: Headers → Request headers.
    - body_str: str → Raw request body as string.

    This function must follow this exact signature to work with Baqo.
    """
    signature = headers.get("x-mycompany-signature")
    if not signature:
        raise Exception("Missing MyCompany signature")

    # Example: simple static match for demo
    if signature != secret:
        raise Exception("Invalid signature")
```

## Usage

In your YAML config:

```yaml
sources:
  mycompany_service:
    type: mycompany_signature
    secret: ${MYCOMPANY_SECRET}
    event_id_path: data.txn_id
```

## How it works

- Baqo automatically scans this folder at startup.
- If your file defines `VERIFICATION_TYPE` and `verify_signature`, it will be loaded and registered.
- Your custom verification logic will then be used when `type` matches.

## What if my webhook does not use a secret?

If your source does not use a secret, you can:

1. Still define the `verify_signature` function with `secret` as a parameter.  
2. Simply ignore `secret` inside your function.

**Example: Accept all requests without checking a secret**

```python
VERIFICATION_TYPE = "open_signature"

from starlette.datastructures import Headers

async def verify_signature(secret: str, headers: Headers, body_str: str):
    # No checks — always accept
    pass
```

**YAML config example:**

```yaml
sources:
  open_service:
    type: open_signature
    event_id_path: data.txn_id
```

## Why keep `secret` in the function signature?

We keep the signature uniform so Baqo can call all verifiers consistently, whether or not they actually use `secret`.
This function must follow this exact signature to work with Baqo.

---

Baqo! 🚀
