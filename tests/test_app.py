from app import app


def test_index_loads():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Email Repository" in response.data


def test_compose_requires_fields():
    client = app.test_client()
    response = client.post("/compose", data={"recipient": "", "subject": "", "body": ""})
    assert response.status_code == 200
    assert b"All fields are required." in response.data


def test_compose_redirects_on_success():
    client = app.test_client()
    response = client.post(
        "/compose",
        data={"recipient": "a@example.com", "subject": "Hi", "body": "hello"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/sent" in response.location
