"""Admin CSV export and its auth guard."""

from tests.conftest import ClientBundle

HEADERS = {"X-Admin-Token": "test-admin-token"}


def test_export_requires_token(client: ClientBundle) -> None:
    assert client.http.get("/api/admin/leads.csv").status_code == 403
    assert (
        client.http.get(
            "/api/admin/leads.csv", headers={"X-Admin-Token": "wrong"}
        ).status_code
        == 403
    )


def test_export_returns_csv(client: ClientBundle) -> None:
    client.http.post("/api/signup", json={"email": "a@example.com", "source": "landing:primer"})
    client.http.post("/api/checkout", json={"email": "b@example.com", "product": "cohort"})

    res = client.http.get("/api/admin/leads.csv", headers=HEADERS)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")

    lines = res.text.strip().splitlines()
    assert lines[0] == "id,email,source,created_at,confirmed_at,primer_sent_at"
    assert len(lines) == 3
    assert "a@example.com" in lines[1]
    assert "waitlist:cohort" in lines[2]
