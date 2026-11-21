"""Owner (JWT) sinh script, tạo job video; phát MP4 qua API; CORS."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import OWNER, SERVICE
from tests.api.fakes import JOB_ID, PRODUCT_ID, FakeDb
from worker.api.deps import get_script_generator, get_settings
from worker.api.errors import DatabaseError
from worker.main import app
from worker.settings import Settings

VIDEO_BODY = {"pkb_version": 1, "script_revision": 1, "idempotency_key": "k"}


def test_owner_tao_job_video(client: TestClient, db: FakeDb) -> None:
    db.tables["products"] = [{"id": PRODUCT_ID, "website_url": "https://x.dev"}]
    db.rpc_results["create_generation_job"] = JOB_ID
    r = client.post(f"/products/{PRODUCT_ID}/videos", json=VIDEO_BODY, headers=OWNER)
    assert r.status_code == 202
    assert db.last("select:products")["jwt"] == "owner-jwt"  # kiểm quyền sở hữu bằng RLS


def test_owner_khong_so_huu_product_404(client: TestClient, db: FakeDb) -> None:
    r = client.post(f"/products/{PRODUCT_ID}/videos", json=VIDEO_BODY, headers=OWNER)
    assert r.status_code == 404
    assert not [c for c in db.calls if c[0] == "rpc:create_generation_job"]


def test_khong_dang_nhap_401(client: TestClient) -> None:
    assert client.post(f"/products/{PRODUCT_ID}/videos", json=VIDEO_BODY).status_code == 401


def test_service_van_tao_job_video(client: TestClient, db: FakeDb) -> None:
    db.rpc_results["create_generation_job"] = JOB_ID
    r = client.post(f"/products/{PRODUCT_ID}/videos", json=VIDEO_BODY, headers=SERVICE)
    assert r.status_code == 202


def test_owner_khong_so_huu_khong_sinh_script(client: TestClient, db: FakeDb) -> None:
    app.dependency_overrides[get_script_generator] = lambda: None
    r = client.post(
        f"/products/{PRODUCT_ID}/scripts/generate",
        json={"knowledge_version": 1, "idempotency_key": "k"},
        headers=OWNER,
    )
    assert r.status_code == 404


def test_db_loi_van_anh_xa(client: TestClient, db: FakeDb) -> None:
    db.tables["products"] = [{"id": PRODUCT_ID}]
    db.errors["create_generation_job"] = DatabaseError(400, "23514", "script chưa duyệt")
    r = client.post(f"/products/{PRODUCT_ID}/videos", json=VIDEO_BODY, headers=OWNER)
    assert r.status_code == 422


@pytest.fixture
def video_dir(tmp_path: Path, client: TestClient) -> Path:
    settings = Settings(video_store_dir=str(tmp_path))
    app.dependency_overrides[get_settings] = lambda: settings
    job_dir = tmp_path / JOB_ID
    job_dir.mkdir()
    (job_dir / "a.mp4").write_bytes(b"0123456789")
    return tmp_path


def _job(db: FakeDb, mp4: str, status: str = "completed") -> None:
    db.tables["generation_jobs"] = [
        {
            "id": JOB_ID,
            "job_type": "video",
            "status": status,
            "result_manifest": {"outputs": [{"ratio": "16:9", "ok": True, "mp4": mp4}]},
        }
    ]


def test_phat_mp4_co_range(client: TestClient, db: FakeDb, video_dir: Path) -> None:
    _job(db, str(video_dir / JOB_ID / "a.mp4"))
    r = client.get(f"/jobs/{JOB_ID}/video", headers={**OWNER, "Range": "bytes=2-4"})
    assert r.status_code == 206
    assert r.content == b"234"
    assert r.headers["content-type"] == "video/mp4"
    assert db.last("select:generation_jobs")["jwt"] == "owner-jwt"


def test_mp4_ngoai_thu_muc_job_bi_chan(client: TestClient, db: FakeDb, video_dir: Path) -> None:
    secret = video_dir / "secret.mp4"
    secret.write_bytes(b"x")
    _job(db, str(secret))
    assert client.get(f"/jobs/{JOB_ID}/video", headers=OWNER).status_code == 404


def test_mp4_job_chua_xong_409(client: TestClient, db: FakeDb, video_dir: Path) -> None:
    _job(db, str(video_dir / JOB_ID / "a.mp4"), status="running")
    assert client.get(f"/jobs/{JOB_ID}/video", headers=OWNER).status_code == 409


def test_mp4_thieu_ratio_404(client: TestClient, db: FakeDb, video_dir: Path) -> None:
    _job(db, str(video_dir / JOB_ID / "a.mp4"))
    assert client.get(f"/jobs/{JOB_ID}/video?ratio=9:16", headers=OWNER).status_code == 404


def test_cors_cho_phep_origin_cua_web(client: TestClient) -> None:
    r = client.options(
        "/products",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    other = client.options(
        "/products",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in other.headers
