import io
import os
import shutil
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.config.security import create_access_token
from src.config.settings import settings
from src.models.profile import Profile
from src.models.user import User


def create_user_helper(db: Session, username: str) -> User:
    uid = str(uuid.uuid4())[:8]
    user = User(
        phone_number=f"+91987{uid}",
        email=f"{username}_{uid}@spreego.com",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = Profile(
        user_id=user.id,
        username=f"{username}_{uid}",
        full_name=f"Full {username}",
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(db_session: Session):
    user = create_user_helper(db_session, "uploader")
    token = create_access_token(user_id=user.id)
    return {"Authorization": f"Bearer {token}"}, user


@pytest.fixture
def other_auth_headers(db_session: Session):
    user = create_user_helper(db_session, "other")
    token = create_access_token(user_id=user.id)
    return {"Authorization": f"Bearer {token}"}, user


@pytest.fixture(autouse=True)
def clean_test_uploads():
    yield
    test_upload_dir = settings.UPLOAD_DIR
    if os.path.exists(test_upload_dir):
        for item in os.listdir(test_upload_dir):
            item_path = os.path.join(test_upload_dir, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                elif os.path.isfile(item_path):
                    os.remove(item_path)
            except Exception:
                pass


def test_presign_upload_valid_video(client: TestClient, auth_headers):
    headers, user = auth_headers
    payload = {
        "file_name": "dance_spree.mp4",
        "content_type": "video/mp4",
        "file_size": 15000000,
        "purpose": "spree_video",
    }
    response = client.post("/api/v1/uploads/presign", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "file_id" in data
    assert "upload_url" in data
    assert data["upload_url"] == f"/api/v1/uploads/{data['file_id']}/file"
    assert "/static/uploads/" in data["media_url"]
    assert data["purpose"] == "spree_video"


def test_presign_upload_valid_image(client: TestClient, auth_headers):
    headers, user = auth_headers
    payload = {
        "file_name": "creator_avatar.png",
        "content_type": "image/png",
        "file_size": 204800,
        "purpose": "avatar",
    }
    response = client.post("/api/v1/uploads/presign", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["purpose"] == "avatar"
    assert data["file_id"] is not None


def test_presign_upload_invalid_mime_for_purpose(client: TestClient, auth_headers):
    headers, user = auth_headers
    payload = {
        "file_name": "avatar.mp4",
        "content_type": "video/mp4",
        "file_size": 500000,
        "purpose": "avatar",
    }
    response = client.post("/api/v1/uploads/presign", json=payload, headers=headers)
    assert response.status_code == 400
    assert "not allowed for purpose" in response.json()["detail"]


def test_presign_upload_unsupported_mime(client: TestClient, auth_headers):
    headers, user = auth_headers
    payload = {
        "file_name": "script.sh",
        "content_type": "text/x-shellscript",
        "file_size": 1024,
        "purpose": "spree_video",
    }
    response = client.post("/api/v1/uploads/presign", json=payload, headers=headers)
    assert response.status_code == 422


def test_presign_upload_exceeds_image_size_limit(client: TestClient, auth_headers):
    headers, user = auth_headers
    payload = {
        "file_name": "huge_pic.jpg",
        "content_type": "image/jpeg",
        "file_size": 30 * 1024 * 1024,
        "purpose": "product_image",
    }
    response = client.post("/api/v1/uploads/presign", json=payload, headers=headers)
    assert response.status_code == 400
    assert "exceeds maximum allowed size" in response.json()["detail"]


def test_presign_upload_unauthenticated(client: TestClient):
    payload = {
        "file_name": "video.mp4",
        "content_type": "video/mp4",
        "file_size": 1024,
        "purpose": "spree_video",
    }
    response = client.post("/api/v1/uploads/presign", json=payload)
    assert response.status_code == 401


def test_upload_file_chunk_success(client: TestClient, auth_headers):
    headers, user = auth_headers
    presign_res = client.post(
        "/api/v1/uploads/presign",
        json={
            "file_name": "sample_clip.mp4",
            "content_type": "video/mp4",
            "file_size": 128,
            "purpose": "spree_video",
        },
        headers=headers,
    )
    assert presign_res.status_code == 201
    file_id = presign_res.json()["file_id"]
    upload_url = presign_res.json()["upload_url"]

    file_content = b"fake-video-binary-content-mp4-test"
    files = {"file": ("sample_clip.mp4", io.BytesIO(file_content), "video/mp4")}
    upload_res = client.post(upload_url, files=files, headers=headers)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["status"] == "COMPLETED"
    assert upload_data["file_size"] == len(file_content)
    assert upload_data["media_url"].startswith("/static/uploads/")

    static_res = client.get(upload_data["media_url"])
    assert static_res.status_code == 200
    assert static_res.content == file_content


def test_direct_upload_success(client: TestClient, auth_headers):
    headers, user = auth_headers
    image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_image_bytes"
    files = {"file": ("direct_avatar.png", io.BytesIO(image_content), "image/png")}
    data = {"purpose": "avatar"}

    response = client.post("/api/v1/uploads/direct", files=files, data=data, headers=headers)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["status"] == "COMPLETED"
    assert res_data["content_type"] == "image/png"
    assert res_data["file_size"] == len(image_content)
    assert res_data["purpose"] == "avatar"

    static_res = client.get(res_data["media_url"])
    assert static_res.status_code == 200
    assert static_res.content == image_content


def test_complete_upload_endpoint(client: TestClient, auth_headers):
    headers, user = auth_headers
    presign_res = client.post(
        "/api/v1/uploads/presign",
        json={
            "file_name": "cover.jpg",
            "content_type": "image/jpeg",
            "file_size": 256,
            "purpose": "open_cover",
        },
        headers=headers,
    )
    file_id = presign_res.json()["file_id"]

    client.post(
        f"/api/v1/uploads/{file_id}/file",
        files={"file": ("cover.jpg", io.BytesIO(b"jpeg-bytes"), "image/jpeg")},
        headers=headers,
    )

    complete_res = client.post(f"/api/v1/uploads/{file_id}/complete", headers=headers)
    assert complete_res.status_code == 200
    assert complete_res.json()["status"] == "COMPLETED"


def test_user_cannot_upload_to_another_users_session(
    client: TestClient, auth_headers, other_auth_headers
):
    headers_a, user_a = auth_headers
    headers_b, user_b = other_auth_headers

    presign_res = client.post(
        "/api/v1/uploads/presign",
        json={
            "file_name": "private_doc.png",
            "content_type": "image/png",
            "file_size": 100,
            "purpose": "avatar",
        },
        headers=headers_a,
    )
    file_id = presign_res.json()["file_id"]

    files = {"file": ("private_doc.png", io.BytesIO(b"malicious"), "image/png")}
    res = client.post(f"/api/v1/uploads/{file_id}/file", files=files, headers=headers_b)
    assert res.status_code == 403
    assert "permission" in res.json()["detail"].lower()


def test_user_cannot_view_another_users_upload_details(
    client: TestClient, auth_headers, other_auth_headers
):
    headers_a, user_a = auth_headers
    headers_b, user_b = other_auth_headers

    files = {"file": ("item.png", io.BytesIO(b"img"), "image/png")}
    res = client.post("/api/v1/uploads/direct", files=files, data={"purpose": "product_image"}, headers=headers_a)
    file_id = res.json()["file_id"]

    view_res = client.get(f"/api/v1/uploads/{file_id}", headers=headers_b)
    assert view_res.status_code == 403


def test_get_my_uploads_list(client: TestClient, auth_headers):
    headers, user = auth_headers
    for i in range(3):
        client.post(
            "/api/v1/uploads/direct",
            files={"file": (f"test_{i}.png", io.BytesIO(f"img_{i}".encode()), "image/png")},
            data={"purpose": "avatar"},
            headers=headers,
        )

    response = client.get("/api/v1/uploads/my", headers=headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    assert all(item["purpose"] == "avatar" for item in items)
