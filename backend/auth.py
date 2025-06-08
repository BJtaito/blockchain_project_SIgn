from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse
import jwt, time, os, uuid
import secrets
from eth_account.messages import encode_defunct
from eth_account import Account

nonces = {}
router = APIRouter()
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "devkey")
JWT_EXPIRE_SECONDS = 1800

@router.post("/verify")
async def verify_signature(payload: dict, response: Response):
    address = payload.get("address")
    signature = payload.get("signature")

    nonce = nonces.get(address.lower())
    if not nonce:
        return JSONResponse(status_code=400, content={"detail": "Nonce not found"})

    # ✅ 프리픽스 포함된 메시지로 서명 복구
    expected_message = f"Sign this message: {nonce}"
    msg = encode_defunct(text=expected_message)
    recovered = Account.recover_message(msg, signature=signature)

    if recovered.lower() != address.lower():
        return JSONResponse(status_code=400, content={"detail": "Signature verification failed"})

    # JWT 발급
    payload = {
        "sub": address,
        "exp": int(time.time()) + JWT_EXPIRE_SECONDS,
        "jti": str(uuid.uuid4())
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS512")

    # 쿠키로 전달
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=JWT_EXPIRE_SECONDS,
        path="/"
    )

    return {"message": "Login successful via signature"}

@router.get("/nonce")
def get_nonce(address: str):
    if not address or not address.startswith("0x") or len(address) != 42:
        return JSONResponse(status_code=400, content={"detail": "Invalid address"})

    nonce = secrets.token_hex(16)
    nonces[address.lower()] = nonce
    return {"nonce": nonce}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/"
    )
    return {"message": "Logout successful"}

@router.get("/me")
def get_me(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS512"])
        return {"address": payload["sub"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")