async def test_ghl_webhook_upserts_lead_and_property(client):
    response = await client.post(
        "/webhooks/ghl",
        json={
            "contact_id": "abc123",
            "first_name": "John",
            "last_name": "Smith",
            "phone": "+14045550100",
            "custom_fields": {
                "property_address": "123 Main St",
                "county": "Gwinnett",
                "situation": "inherited",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    leads = await client.get("/api/leads", params={"county": "Gwinnett", "status": "new"})
    assert leads.status_code == 200
    body = leads.json()
    assert body["count"] == 1
    assert body["leads"][0]["property"]["address"] == "123 Main St"
