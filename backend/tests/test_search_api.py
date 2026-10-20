from fastapi.testclient import TestClient

from tests.pdf_factory import make_pdf


def upload(client: TestClient, pages: list[str | None], name: str) -> dict:
    response = client.post(
        "/api/documents",
        files={"file": (name, make_pdf(pages), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


def test_search_returns_matching_passage_and_page(api_client: TestClient) -> None:
    upload(
        api_client,
        ["An introduction to gardens.", "Secure document retrieval finds relevant passages."],
        "report.pdf",
    )

    response = api_client.get(
        "/api/documents/search",
        params={"q": "secure document retrieval"},
    )

    assert response.status_code == 200
    results = response.json()
    assert results
    assert results[0]["filename"] == "report.pdf"
    assert results[0]["page_number"] == 2
    assert results[0]["document_id"]
    assert "retrieval" in results[0]["text"]
    assert results[0]["score"] > 0


def test_search_can_filter_to_one_document(api_client: TestClient) -> None:
    first = upload(api_client, ["Project keyword in first document."], "first.pdf")
    second = upload(api_client, ["Project keyword in second document."], "second.pdf")

    response = api_client.get(
        "/api/documents/search",
        params={"q": "project keyword", "document_id": second["id"]},
    )

    assert response.status_code == 200
    results = response.json()
    assert results
    assert {result["document_id"] for result in results} == {second["id"]}
    assert {result["filename"] for result in results} == {"second.pdf"}
    assert first["id"] not in {result["document_id"] for result in results}


def test_search_returns_empty_list_for_no_match(api_client: TestClient) -> None:
    upload(api_client, ["A document about gardens."], "garden.pdf")

    response = api_client.get(
        "/api/documents/search",
        params={"q": "quantum spacecraft"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search_validates_query_and_limit(api_client: TestClient) -> None:
    assert api_client.get("/api/documents/search").status_code == 422
    assert (
        api_client.get("/api/documents/search", params={"q": "garden", "limit": 0}).status_code
        == 422
    )
    assert (
        api_client.get("/api/documents/search", params={"q": "garden", "limit": 21}).status_code
        == 422
    )


def test_search_validates_document_id(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/documents/search",
        params={"q": "garden", "document_id": "not-an-id"},
    )
    assert response.status_code == 422
