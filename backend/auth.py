from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
import jwt, time, os, uuid

router = APIRouter()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_EXPIRE_SECONDS = 1800

@router.post("/login")
async def login(request: Request, response: Response):  # ✅ response 인자로 받아야 함
    data = await request.json()
    address = data.get("address")

    if not address or not address.startswith("0x") or len(address) != 42:
        return JSONResponse(status_code=400, content={"detail": "Invalid wallet address"})

    payload = {
        "sub": address,
        "exp": int(time.time()) + JWT_EXPIRE_SECONDS,
        "jti": str(uuid.uuid4())  # ✅ JWT ID 추가 (선택적으로 추후 블랙리스트 관리에도 활용 가능)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS512")

    # ✅ HttpOnly 쿠키로 설정
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # 실제 운영 시 True (HTTPS 사용 조건)
        samesite="Lax",
        max_age=JWT_EXPIRE_SECONDS,
        path="/"
    )

    return {"message": "Login successful"}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/"
    )
    return {"message": "Logout successful"}