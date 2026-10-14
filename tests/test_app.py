
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


def test_ask_rejects_empty_question():
    """Check that an empty question returns a 400 error."""
    client = app_module.app.test_client()

    response = client.post(
        "/ask",
        json={"question": ""}
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Please enter a question."
    }


def test_ask_rejects_non_string_question():
    """Check that a question that is not text returns a 400 error."""
    client = app_module.app.test_client()

    response = client.post(
        "/ask",
        json={"question": 123}
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Please enter a question."
    }


def test_read_study_document_success(tmp_path, monkeypatch):
    """Check that a valid text document can be read."""
    study_file = tmp_path / "test_document.txt"
    study_file.write_text(
        "Plants use sunlight for photosynthesis.",
        encoding="utf-8"
    )

    monkeypatch.setattr(
        app_module,
        "STUDY_MATERIAL_DIR",
        tmp_path
    )

    result = app_module.read_study_document("test_document.txt")

    assert result == "Plants use sunlight for photosynthesis."


def test_read_study_document_rejects_path_traversal():
    """Check that paths trying to leave the study folder are rejected."""
    unsafe_names = [
        "../secret.txt",
        "..\\secret.txt",
        "folder/document.txt",
        "folder\\document.txt",
    ]

    for document_name in unsafe_names:
        try:
            app_module.read_study_document(document_name)
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"Unsafe document name was accepted: {document_name}"
            )


def test_read_study_document_rejects_non_txt_file():
    """Check that files with other extensions are rejected."""
    try:
        app_module.read_study_document("notes.pdf")
    except ValueError:
        pass
    else:
        raise AssertionError("A non-text file was accepted.")


def test_read_study_document_rejects_missing_file(tmp_path, monkeypatch):
    """Check that a missing document raises FileNotFoundError."""
    monkeypatch.setattr(
        app_module,
        "STUDY_MATERIAL_DIR",
        tmp_path
    )

    try:
        app_module.read_study_document("missing.txt")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("A missing document was accepted.")
