def test_settings_page_and_add_task(client):
    assert client.get("/settings").status_code == 200
    client.post("/settings/task-types", data={"name": "Analysis"}, follow_redirects=False)
    page = client.get("/settings")
    assert "Analysis" in page.text


def test_save_settings(client):
    client.post("/settings", data={"default_hourly_rate": "200", "currency_symbol": "$"}, follow_redirects=False)
    assert "200.00" in client.get("/settings").text
