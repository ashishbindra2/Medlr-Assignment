import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_extract_medicine_success():
    response = client.get("/extract-medicine", json={"url": "https://1mg.com/drugs/actorise-25-injection-228329"})
    assert response.status_code == 200
    assert "medicine_name" in response.json()

@pytest.mark.asyncio
async def test_store_data_success():
    response = client.post(
        "/store-data",
        json={
            "collection_name": "users",
            "data": {"user_id": "12345", "name": "John Doe", "email": "john@example.com"},
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
