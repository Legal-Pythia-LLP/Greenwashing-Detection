from fastapi.testclient import TestClient
from app.main import app

def test_root():
    client = TestClient(app)
    response = client.get("/v1/docs")
    assert response.status_code == 200 