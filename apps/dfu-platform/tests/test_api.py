import io
import os
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
TEST_DB = ROOT / "tests" / "test_api.db"
TEST_DB.unlink(missing_ok=True)
sys.path.insert(0, str(BACKEND))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["DFU_SKIP_MODEL_PRELOAD"] = "1"
os.environ["DFU_DEV_SHOW_CODE"] = "1"
os.environ["DFU_INITIAL_DOCTOR_INVITE"] = "ritanai"

from fastapi.testclient import TestClient

import main


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_patient_doctor_profile_and_record_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    monkeypatch.setattr(
        main,
        "run_model_prediction",
        lambda image: {
            "status": "ok",
            "grade": "Grade 2",
            "grade_index": 1,
            "confidence": 0.82,
            "probabilities": [0.05, 0.82, 0.1, 0.03],
            "is_borderline": False,
            "secondary_grade": None,
            "secondary_confidence": None,
            "skin_ratio": 0.5,
        },
    )

    with TestClient(main.app) as client:
        sent = client.post("/api/email/send-code", json={"email": "patient@example.com"})
        assert sent.status_code == 200
        code = sent.json()["dev_code"]

        registered = client.post(
            "/api/email/register",
            json={"email": "patient@example.com", "code": code, "password": "Patient1!"},
        )
        assert registered.status_code == 200
        patient_token = registered.json()["data"]["access_token"]

        initial_profile = client.get("/api/patient/profile", headers=auth(patient_token))
        assert initial_profile.json()["profile"]["profile_completed"] is False

        options = client.get("/api/patient/dietary-options", headers=auth(patient_token)).json()["options"]
        assert len(options) == 8

        profile = client.put(
            "/api/patient/profile",
            headers=auth(patient_token),
            json={
                "name": "测试患者",
                "sex": "female",
                "residence": "广东省深圳市",
                "dietary_habits": ["balanced", "low_produce"],
            },
        )
        assert profile.status_code == 200
        assert profile.json()["profile"]["profile_completed"] is True

        doctor_register = client.post(
            "/api/doctor/register",
            json={
                "username": "doctor_test",
                "real_name": "测试医生",
                "password": "Doctor1!",
                "invitation_code": "ritanai",
                "institution": "测试医院",
                "department": "内分泌科",
            },
        )
        assert doctor_register.status_code == 200
        doctor_token = doctor_register.json()["data"]["access_token"]

        lookup = client.post(
            "/api/doctor/patients/lookup",
            headers=auth(doctor_token),
            json={"email": "patient@example.com"},
        )
        assert lookup.status_code == 200
        patient_id = lookup.json()["patient"]["id"]

        image = Image.new("RGB", (64, 64), (180, 80, 70))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        without_consent = client.post(
            f"/api/doctor/patients/{patient_id}/predict",
            headers=auth(doctor_token),
            files={"image": ("wound.jpg", buffer.getvalue(), "image/jpeg")},
        )
        assert without_consent.status_code == 400

        predicted = client.post(
            f"/api/doctor/patients/{patient_id}/predict",
            headers=auth(doctor_token),
            data={"consent_confirmed": "true"},
            files={"image": ("wound.jpg", buffer.getvalue(), "image/jpeg")},
        )
        assert predicted.status_code == 200
        assert predicted.json()["status"] == "ok"
        assert predicted.json()["record_id"] is not None

        patient_records = client.get("/api/records", headers=auth(patient_token))
        assert len(patient_records.json()["records"]) == 1
        assert patient_records.json()["records"][0]["source"] == "doctor"

        dashboard = client.get("/api/doctor/dashboard", headers=auth(doctor_token))
        assert dashboard.status_code == 200
        assert dashboard.json()["summary"] == {
            "patients": 1,
            "records": 1,
            "today_records": 1,
            "high_risk": 0,
        }
