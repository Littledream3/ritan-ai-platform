import io
import os
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TEST_DB = ROOT / "tests" / "media-drop-test.db"
TEST_DB.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app import main
from app.models import UploadBatch


Base.metadata.create_all(engine)


def jpeg_bytes() -> bytes:
    image = Image.new("RGB", (640, 480), (60, 120, 170))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_anonymous_batch_upload_and_isolation(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(main, "DISK_RESERVE_BYTES", 0)

    with TestClient(main.app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["database"] == "isolated"

        created = client.post("/api/batches")
        assert created.status_code == 200
        batch_id = created.json()["batch"]["id"]
        token = created.json()["upload_token"]
        headers = {"X-Upload-Token": token}

        with SessionLocal() as db:
            row = db.get(UploadBatch, batch_id)
            assert row.upload_token_hash != token
            assert len(row.upload_token_hash) == 64

        unauthorized = client.post(
            f"/api/batches/{batch_id}/files",
            files={"file": ("photo.jpg", jpeg_bytes(), "image/jpeg")},
        )
        assert unauthorized.status_code == 401

        invalid = client.post(
            f"/api/batches/{batch_id}/files",
            headers=headers,
            files={"file": ("notes.txt", b"not-media", "text/plain")},
        )
        assert invalid.status_code == 400

        image = jpeg_bytes()
        uploaded_image = client.post(
            f"/api/batches/{batch_id}/files",
            headers=headers,
            files={"file": ("foot.jpg", image, "image/jpeg")},
        )
        assert uploaded_image.status_code == 200
        assert uploaded_image.json()["file"]["kind"] == "image"

        duplicate = client.post(
            f"/api/batches/{batch_id}/files",
            headers=headers,
            files={"file": ("copy.jpg", image, "image/jpeg")},
        )
        assert duplicate.status_code == 409

        monkeypatch.setattr(main, "validate_video", lambda path, supplied_type: (".mp4", "video/mp4", 8.25))
        uploaded_video = client.post(
            f"/api/batches/{batch_id}/files",
            headers=headers,
            files={"file": ("clip.mp4", b"video-payload", "video/mp4")},
        )
        assert uploaded_video.status_code == 200
        assert uploaded_video.json()["file"]["kind"] == "video"
        assert uploaded_video.json()["file"]["duration_seconds"] == 8.25

        detail = client.get(f"/api/batches/{batch_id}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["batch"]["file_count"] == 2
        assert len(detail.json()["batch"]["files"]) == 2

        completed = client.post(f"/api/batches/{batch_id}/complete", headers=headers)
        assert completed.status_code == 200
        assert completed.json()["batch"]["status"] == "completed"
        assert completed.json()["batch"]["file_count"] == 2
        assert len(list(tmp_path.rglob("*.*"))) == 2

        locked = client.post(
            f"/api/batches/{batch_id}/files",
            headers=headers,
            files={"file": ("later.jpg", jpeg_bytes(), "image/jpeg")},
        )
        assert locked.status_code == 409
