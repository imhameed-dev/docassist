from fastapi.testclient import TestClient

from tests.pdf_factory import make_pdf


def upload(client: TestClient, pages: list[str | None], name: str) -> dict:
    response = client.post(
        "/api/documents",
        files={"file": (name, make_pdf(pages), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


def test_answer_returns_evidence_and_page_citation(api_client: TestClient) -> None:
    upload(
        api_client,
        [
            "Gardens need sunlight and water.",
            "Secure document retrieval uses relevant passages and page citations.",
        ],
        "report.pdf",
    )

    response = api_client.post(
        "/api/answer",
        json={"question": "How does secure document retrieval work?"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["insufficient_evidence"] is False
    assert "Secure document retrieval" in result["answer"]
    assert result["citations"]
    assert result["citations"][0]["filename"] == "report.pdf"
    assert result["citations"][0]["page_number"] == 2
    assert result["citations"][0]["excerpt"]


def test_answer_reports_insufficient_evidence(api_client: TestClient) -> None:
    upload(api_client, ["A document about gardens and flowers."], "garden.pdf")

    response = api_client.post(
        "/api/answer",
        json={"question": "What is the quantum spacecraft propulsion system?"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["insufficient_evidence"] is True
    assert result["citations"] == []
    assert "couldn't find relevant evidence" in result["answer"]


def test_answer_can_filter_to_one_document(api_client: TestClient) -> None:
    upload(api_client, ["Project planning uses a weekly schedule."], "first.pdf")
    second = upload(
        api_client,
        ["Project planning uses a monthly schedule."],
        "second.pdf",
    )

    response = api_client.post(
        "/api/answer",
        json={
            "question": "Project planning schedule",
            "document_id": second["id"],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["insufficient_evidence"] is False
    assert {citation["filename"] for citation in result["citations"]} == {"second.pdf"}


def test_answer_validates_request(api_client: TestClient) -> None:
    assert api_client.post("/api/answer", json={}).status_code == 422
    assert (
        api_client.post(
            "/api/answer",
            json={"question": "garden", "document_id": "invalid"},
        ).status_code
        == 422
    )
    assert (
        api_client.post(
            "/api/answer",
            json={"question": "garden", "limit": 0},
        ).status_code
        == 422
    )


def test_answer_cites_multiple_matching_pages(api_client: TestClient) -> None:
    upload(
        api_client,
        [
            "Secure document retrieval finds relevant passages.",
            "Secure document retrieval preserves page citations.",
        ],
        "multi-page.pdf",
    )

    response = api_client.post(
        "/api/answer",
        json={"question": "secure document retrieval"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["insufficient_evidence"] is False
    assert {citation["page_number"] for citation in result["citations"]} == {1, 2}
    assert {citation["filename"] for citation in result["citations"]} == {"multi-page.pdf"}
