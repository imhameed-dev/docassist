from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Document, Page
from tests.pdf_factory import make_encrypted_pdf, make_pdf

MB = 1024 * 1024


def upload(client: TestClient, data: bytes, name: str = "report.pdf") -> Any:
    return client.post("/api/documents", files={"file": (name, data, "application/pdf")})


def stored_files(settings: Settings) -> list[Path]:
    return sorted(settings.uploads_dir.glob("*")) if settings.uploads_dir.exists() else []


def count(engine: Engine, model: type[Document] | type[Page]) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


def test_upload_text_pdf_is_ready(
    api_client: TestClient, settings: Settings, engine: Engine
) -> None:
    response = upload(api_client, make_pdf(["Alpha", "Beta"]))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["filename"] == "report.pdf"
    assert body["page_count"] == 2
    assert body["empty_page_count"] == 0
    assert body["error_code"] is None
    assert [p.name for p in stored_files(settings)] == [f"{body['id']}.pdf"]
    assert count(engine, Page) == 2


def test_page_text_and_numbers_are_stored(api_client: TestClient, engine: Engine) -> None:
    upload(api_client, make_pdf(["Alpha", "Beta"]))
    with Session(engine) as session:
        pages = session.scalars(select(Page).order_by(Page.page_number)).all()
    assert [(p.page_number, p.text) for p in pages] == [(1, "Alpha"), (2, "Beta")]


def test_mixed_pdf_reports_pages_without_text(api_client: TestClient) -> None:
    body = upload(api_client, make_pdf(["Text", None, "More"])).json()
    assert body["status"] == "ready"
    assert body["page_count"] == 3
    assert body["empty_page_count"] == 1


def test_scanned_pdf_is_flagged_as_needing_ocr(
    api_client: TestClient, settings: Settings, engine: Engine
) -> None:
    body = upload(api_client, make_pdf([None, None])).json()
    assert body["status"] == "needs_ocr"
    assert body["error_code"] == "needs_ocr"
    assert "OCR" in body["error_message"]
    assert body["page_count"] == 2
    assert len(stored_files(settings)) == 1  # original kept so OCR can be added later
    assert count(engine, Page) == 0  # no fake text is stored


def test_corrupted_pdf_is_recorded_as_failed_and_file_removed(
    api_client: TestClient, settings: Settings
) -> None:
    response = upload(api_client, b"%PDF-1.4\nnot really a pdf")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_code"] == "corrupted"
    assert stored_files(settings) == []


def test_encrypted_pdf_is_recorded_as_failed(api_client: TestClient) -> None:
    body = upload(api_client, make_encrypted_pdf()).json()
    assert body["status"] == "failed"
    assert body["error_code"] == "encrypted"


def test_pdf_over_page_limit_is_recorded_as_failed(api_client: TestClient) -> None:
    body = upload(api_client, make_pdf(["p"] * 6)).json()  # fixture limit is 5 pages
    assert body["status"] == "failed"
    assert body["error_code"] == "too_many_pages"


def test_non_pdf_renamed_to_pdf_is_rejected(
    api_client: TestClient, settings: Settings, engine: Engine
) -> None:
    response = upload(api_client, b"MZ\x90\x00 definitely an executable", "invoice.pdf")
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "not_a_pdf"
    assert stored_files(settings) == []
    assert count(engine, Document) == 0


def test_empty_file_is_rejected(api_client: TestClient, settings: Settings) -> None:
    response = upload(api_client, b"")
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "empty_file"
    assert stored_files(settings) == []


def test_oversized_file_is_rejected_and_not_stored(
    api_client: TestClient, settings: Settings, engine: Engine
) -> None:
    response = upload(api_client, b"%PDF-1.4\n" + b"0" * MB)  # limit is 1 MB
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "file_too_large"
    assert stored_files(settings) == []
    assert count(engine, Document) == 0


def test_missing_file_part_is_a_client_error(api_client: TestClient) -> None:
    assert api_client.post("/api/documents").status_code == 422


def test_hostile_filename_cannot_escape_the_uploads_directory(
    api_client: TestClient, settings: Settings, tmp_path: Path
) -> None:
    body = upload(api_client, make_pdf(["x"]), "../../evil.pdf").json()
    assert body["filename"] == "evil.pdf"
    assert [p.name for p in stored_files(settings)] == [f"{body['id']}.pdf"]
    assert not list(tmp_path.rglob("evil.pdf"))


def test_list_and_get_documents(api_client: TestClient) -> None:
    first = upload(api_client, make_pdf(["one"]), "one.pdf").json()
    second = upload(api_client, make_pdf(["two"]), "two.pdf").json()
    listed = api_client.get("/api/documents").json()
    assert {d["id"] for d in listed} == {first["id"], second["id"]}
    fetched = api_client.get(f"/api/documents/{first['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["filename"] == "one.pdf"


def test_empty_list(api_client: TestClient) -> None:
    assert api_client.get("/api/documents").json() == []


def test_unknown_document_is_404(api_client: TestClient) -> None:
    unknown = "0" * 32
    assert api_client.get(f"/api/documents/{unknown}").status_code == 404
    assert api_client.delete(f"/api/documents/{unknown}").status_code == 404


def test_malformed_document_id_is_rejected(api_client: TestClient) -> None:
    assert api_client.get("/api/documents/not-a-valid-id").status_code == 422
    assert api_client.delete("/api/documents/..%2F..%2Fetc%2Fpasswd").status_code in (404, 422)


def test_delete_removes_rows_and_stored_file(
    api_client: TestClient, settings: Settings, engine: Engine
) -> None:
    body = upload(api_client, make_pdf(["a", "b"])).json()
    assert len(stored_files(settings)) == 1
    response = api_client.delete(f"/api/documents/{body['id']}")
    assert response.status_code == 204
    assert stored_files(settings) == []
    assert count(engine, Document) == 0
    assert count(engine, Page) == 0
    assert api_client.get(f"/api/documents/{body['id']}").status_code == 404
