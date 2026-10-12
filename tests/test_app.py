import backend.app as app_module


def test_home_route():
    """Check that the backend home route works."""
    client = app_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "AI Study Assistant 2.0 backend is running"
    }


def test_documents_route(tmp_path, monkeypatch):
    """Check that the backend lists available text documents."""
    study_file = tmp_path / "test_document.txt"
    study_file.write_text(
        "This is a test study document.",
        encoding="utf-8"
    )

    # Use a temporary folder so the real study files are not changed.
    monkeypatch.setattr(
        app_module,
        "STUDY_MATERIAL_DIR",
        tmp_path
    )

    client = app_module.app.test_client()
    response = client.get("/documents")

    assert response.status_code == 200
    assert response.get_json() == {
        "documents": ["test_document.txt"]
    }


def test_documents_route_when_folder_is_empty(tmp_path, monkeypatch):
    """Check that an empty folder returns an empty document list."""
    monkeypatch.setattr(
        app_module,
        "STUDY_MATERIAL_DIR",
        tmp_path
    )

    client = app_module.app.test_client()
    response = client.get("/documents")

    assert response.status_code == 200
    assert response.get_json() == {
        "documents": []
    }