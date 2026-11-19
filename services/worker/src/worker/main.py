from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from worker.api.errors import ApiError, error_body
from worker.api.routes import router
from worker.settings import MissingConfigError, Settings

app = FastAPI(title="AI Review Content Factory — Worker")
app.include_router(router)
# CORS cho web (trình duyệt gọi thẳng worker bằng Bearer token, không dùng cookie).
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(Settings.from_env().cors_origins),
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content=error_body(exc.detail))


@app.exception_handler(MissingConfigError)
async def missing_config_handler(_: Request, exc: MissingConfigError) -> JSONResponse:
    # Chỉ có tên biến, không có giá trị.
    return JSONResponse(status_code=503, content=error_body(str(exc)))


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Không trả lại giá trị người gửi (có thể chứa dữ liệu nhạy cảm); chỉ vị trí và lý do.
    detail = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(status_code=422, content=error_body(detail))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
