"""Endpoint P1: Product → PKB → script → job. Hợp đồng: `docs/specs/p1-pipeline-db-contract.md`.

Quyền:
- Owner (token Supabase): tạo product, tạo job crawl, đọc dữ liệu của mình (RLS), duyệt PKB/script.
- Service (X-Service-Token, n8n/worker): tạo PKB version, script revision, job video, cập nhật job.
Ghi luôn đi qua RPC `service_role`; quyền sở hữu khi duyệt do RPC kiểm bằng `p_actor`.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from starlette.concurrency import run_in_threadpool

from worker.api.db import Database, Row
from worker.api.deps import (
    Owner,
    Service,
    current_owner,
    get_db,
    get_script_generator,
    owner_or_service,
    require_service,
)
from worker.api.errors import ApiError, DatabaseError
from worker.api.generator import ScriptGenerationError, ScriptGenerator
from worker.api.m2_input import build_m2_input, input_context
from worker.api.schemas import (
    CrawlRequest,
    JobCreated,
    JobPatch,
    PkbCreate,
    ProductCreate,
    ProductOut,
    Review,
    ReviewOut,
    RevisionCreated,
    ScriptCreate,
    ScriptGenerate,
    VersionCreated,
    VideoRequest,
)
from worker.m1.url import InvalidUrlError, normalize_product_url

router = APIRouter()

Db = Annotated[Database, Depends(get_db)]
OwnerDep = Annotated[Owner, Depends(current_owner)]
ServiceDep = Annotated[Service, Depends(require_service)]
AnyoneDep = Annotated[Owner | Service, Depends(owner_or_service)]


def _db_call(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Gọi database và đổi `DatabaseError` thành `ApiError` theo SQLSTATE."""
    try:
        return fn(*args, **kwargs)
    except DatabaseError as e:
        raise e.to_api_error() from e


def _read(db: Database, who: Owner | Service, table: str, filters: dict[str, str]) -> list[Row]:
    """Owner đọc bằng token của họ (RLS); service đọc toàn bộ."""
    jwt = who.jwt if isinstance(who, Owner) else None
    return _db_call(db.select, table, filters, jwt)


def _one(rows: list[Row], what: str) -> Row:
    if not rows:
        raise ApiError(404, f"không thấy {what}")
    return rows[0]


def _product(db: Database, who: Owner | Service, product_id: UUID) -> Row:
    return _one(_read(db, who, "products", {"id": f"eq.{product_id}"}), "product")


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(body: ProductCreate, owner: OwnerDep, db: Db) -> Any:
    try:
        url = normalize_product_url(body.website_url)
    except InvalidUrlError as e:
        raise ApiError(422, f"website_url: {e}") from e
    merchants = _db_call(db.select, "merchants", {"user_id": f"eq.{owner.id}", "select": "id"})
    merchant = _one(merchants, "hồ sơ merchant của tài khoản này (đăng ký merchant trước)")
    row = {"merchant_id": merchant["id"], "website_url": url}
    if body.name:
        row["name"] = body.name.strip()
    try:
        return _db_call(db.insert, "products", row)
    except ApiError as e:
        if e.status == 409:
            raise ApiError(409, "website_url đã tồn tại") from e
        raise


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: UUID, who: AnyoneDep, db: Db) -> Any:
    return _product(db, who, product_id)


@router.post("/products/{product_id}/crawl", response_model=JobCreated, status_code=202)
def create_crawl_job(product_id: UUID, body: CrawlRequest, who: AnyoneDep, db: Db) -> Any:
    product = _product(db, who, product_id)
    job_id = _db_call(
        db.rpc,
        "create_generation_job",
        {
            "p_product_id": str(product_id),
            "p_job_type": "crawl",
            "p_idempotency_key": body.idempotency_key,
            "p_input_snapshot": {"website_url": product["website_url"]},
            "p_n8n_execution_id": body.n8n_execution_id,
        },
    )
    return {"job_id": job_id}


@router.post("/products/{product_id}/videos", response_model=JobCreated, status_code=202)
def create_video_job(product_id: UUID, body: VideoRequest, _: ServiceDep, db: Db) -> Any:
    job_id = _db_call(
        db.rpc,
        "create_generation_job",
        {
            "p_product_id": str(product_id),
            "p_job_type": "video",
            "p_idempotency_key": body.idempotency_key,
            "p_input_snapshot": {
                "pkb_version": body.pkb_version,
                "script_revision": body.script_revision,
                "render_profile": body.render_profile,
                "options": body.options,
            },
            "p_pkb_version": body.pkb_version,
            "p_script_revision": body.script_revision,
            "p_n8n_execution_id": body.n8n_execution_id,
            "p_render_profile": body.render_profile,
        },
    )
    return {"job_id": job_id}


JOB_COLUMNS = (
    "id,product_id,job_type,status,error,attempts,pkb_version,script_revision,render_profile,"
    "n8n_execution_id,result_manifest,cost_usd,cost_breakdown,created_at,finished_at"
)


@router.get("/jobs/{job_id}")
def get_job(job_id: UUID, who: AnyoneDep, db: Db) -> Any:
    return _one(
        _read(db, who, "generation_jobs", {"id": f"eq.{job_id}", "select": JOB_COLUMNS}), "job"
    )


@router.patch("/jobs/{job_id}")
def patch_job(job_id: UUID, body: JobPatch, _: ServiceDep, db: Db) -> Any:
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise ApiError(422, "không có trường nào để cập nhật")
    rows = _db_call(db.update, "generation_jobs", {"id": f"eq.{job_id}"}, patch)
    return _one(rows, "job")


@router.post("/products/{product_id}/pkb", response_model=VersionCreated, status_code=201)
def create_pkb(product_id: UUID, body: PkbCreate, _: ServiceDep, db: Db) -> Any:
    version = _db_call(
        db.rpc,
        "create_pkb_version",
        {"p_product_id": str(product_id), "p_data": body.data, "p_sources": body.sources},
    )
    return {"version": version}


@router.get("/products/{product_id}/pkb/{version}")
def get_pkb(product_id: UUID, version: int, who: AnyoneDep, db: Db) -> Any:
    filters = {"product_id": f"eq.{product_id}", "version": f"eq.{version}"}
    return _one(_read(db, who, "product_knowledge", filters), "PKB version")


@router.post("/products/{product_id}/pkb/{version}/review", response_model=ReviewOut)
def review_pkb(product_id: UUID, version: int, body: Review, owner: OwnerDep, db: Db) -> Any:
    _db_call(
        db.rpc,
        "review_pkb",
        {
            "p_product_id": str(product_id),
            "p_version": version,
            "p_actor": owner.id,
            "p_decision": body.decision,
            "p_note": body.note,
        },
    )
    filters = {"product_id": f"eq.{product_id}", "version": f"eq.{version}", "select": "status"}
    return _one(_db_call(db.select, "product_knowledge", filters, owner.jwt), "PKB version")


@router.post("/products/{product_id}/scripts", response_model=RevisionCreated, status_code=201)
def create_script(product_id: UUID, body: ScriptCreate, _: ServiceDep, db: Db) -> Any:
    revision = _db_call(
        db.rpc,
        "create_script_revision",
        {
            "p_product_id": str(product_id),
            "p_knowledge_version": body.knowledge_version,
            "p_content": body.content,
            "p_idempotency_key": body.idempotency_key,
            "p_parent_revision": body.parent_revision,
            "p_report": body.report,
            "p_cost_breakdown": body.cost_breakdown,
        },
    )
    return {"revision": revision}


@router.post(
    "/products/{product_id}/scripts/generate", response_model=RevisionCreated, status_code=201
)
async def generate_script(
    product_id: UUID,
    body: ScriptGenerate,
    response: Response,
    _: ServiceDep,
    db: Db,
    generator: Annotated[ScriptGenerator | None, Depends(get_script_generator)],
) -> Any:
    """Sinh script (M2) từ PKB `approved` rồi lưu thành revision `draft`. Chạy đồng bộ (LLM)."""
    pid = str(product_id)
    # Cùng key trả revision cũ, không gọi LLM lần nữa (idempotent, tiết kiệm quota).
    prior = await run_in_threadpool(
        _db_call,
        db.select,
        "script_revisions",
        {"product_id": f"eq.{pid}", "idempotency_key": f"eq.{body.idempotency_key}"},
    )
    if prior:
        response.status_code = 200
        return {"revision": prior[0]["revision"]}
    if generator is None:
        raise ApiError(503, "bộ sinh script (M2) chưa được cấu hình")

    rows = await run_in_threadpool(
        _db_call,
        db.select,
        "product_knowledge",
        {"product_id": f"eq.{pid}", "version": f"eq.{body.knowledge_version}"},
    )
    pkb = _one(rows, "PKB version")
    if pkb["status"] != "approved":
        raise ApiError(422, f"PKB version {body.knowledge_version} chưa được duyệt")
    m2_input = build_m2_input(
        pid, body.knowledge_version, pkb, body.permitted_assets, body.content_context
    )
    try:
        qa = [f.model_dump(exclude_none=True) for f in body.qa_feedback]
        script = await generator(m2_input, qa or None)
    except ScriptGenerationError as e:
        status = 422 if e.invalid else 502
        suffix = " (có thể thử lại)" if e.retryable else ""
        raise ApiError(status, f"sinh script thất bại: {e.message}{suffix}") from e

    revision = await run_in_threadpool(
        _db_call,
        db.rpc,
        "create_script_revision",
        {
            "p_product_id": pid,
            "p_knowledge_version": body.knowledge_version,
            "p_content": script.content,
            "p_idempotency_key": body.idempotency_key,
            "p_parent_revision": body.parent_revision,
            # Lưu phần input không suy ra được từ PKB để runner video kiểm lại kịch bản.
            "p_report": {
                **script.report,
                "input": input_context(body.permitted_assets, body.content_context),
            },
            "p_cost_breakdown": script.cost_breakdown,
        },
    )
    return {"revision": revision}


@router.get("/products/{product_id}/scripts/{revision}")
def get_script(product_id: UUID, revision: int, who: AnyoneDep, db: Db) -> Any:
    filters = {"product_id": f"eq.{product_id}", "revision": f"eq.{revision}"}
    return _one(_read(db, who, "script_revisions", filters), "script revision")


@router.post("/products/{product_id}/scripts/{revision}/review", response_model=ReviewOut)
def review_script(product_id: UUID, revision: int, body: Review, owner: OwnerDep, db: Db) -> Any:
    _db_call(
        db.rpc,
        "review_script_revision",
        {
            "p_product_id": str(product_id),
            "p_revision": revision,
            "p_actor": owner.id,
            "p_decision": body.decision,
            "p_note": body.note,
        },
    )
    filters = {"product_id": f"eq.{product_id}", "revision": f"eq.{revision}", "select": "status"}
    return _one(_db_call(db.select, "script_revisions", filters, owner.jwt), "script revision")
