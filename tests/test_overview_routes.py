def test_overview_shows_project_card(client):
    client.post("/projects/new", data={"client_name": "Acme", "name": "Site",
                "hourly_rate": "150", "budget": "1000", "description": ""}, follow_redirects=False)
    page = client.get("/")
    assert "Acme" in page.text
    assert "remaining" in page.text  # has a budget
