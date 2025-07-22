VERIFICATION_TYPE = "mycompany_signature"

from fastapi import HTTPException
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
        raise HTTPException(status_code=400, detail="Missing MyCompany signature")

    if signature != secret:
        raise HTTPException(status_code=400, detail="Invalid signature")
