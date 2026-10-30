
import backend.app as app_module


def test_home_route():
    """The public home route should work."""
    client = app_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "AI Study Assistant 2.0 backend is running"
    }


def test_documents_route_requires_authentication():
    """Documents must not be accessible without login."""
    client = app_module.app.test_client()

    response = client.get("/documents")

    assert response.status_code in (401, 503)


def test_ask_requires_authentication():
    """Asking questions must require login."""
    client = app_module.app.test_client()

    response = client.post("/ask", json={"question": "Hello"})

    assert response.status_code in (401, 503)


def test_validate_document_name_accepts_txt():
    name, error = app_module.validate_document_name(
        "Biology/photosynthesis.txt"
    )

    assert name == "Biology/photosynthesis.txt"
    assert error is None


def test_validate_document_name_rejects_unsafe_paths():
    """Unsafe paths must be rejected."""
    unsafe_names = [
        "../secret.txt",
        "..\\secret.txt",
        "folder/../secret.txt",
        "folder\\..\\secret.txt",
        "/secret.txt",
        "C:\\secret.txt",
        ".hidden.txt",
        "notes.pdf",
        "",
        None,
        123,
    ]

    for document_name in unsafe_names:
        name, error = app_module.validate_document_name(document_name)

        assert name is None, (
            f"Unsafe document name was accepted: {document_name!r}"
        )
        assert error


def test_read_study_document_success(tmp_path, monkeypatch):
    """A valid local document should return content and no error."""
    study_file = tmp_path / "test_document.txt"
    study_file.write_text(
        "Plants use sunlight for photosynthesis.",
        encoding="utf-8",
    )

    monkeypatch.setattr(app_module, "STUDY_MATERIAL_DIR", tmp_path)
    monkeypatch.setattr(app_module, "BACKEND_MATERIAL_DIR", tmp_path)
    monkeypatch.setattr(app_module, "S3_BUCKET_NAME", "")
    monkeypatch.setattr(app_module, "s3_client", None)

    content, error = app_module.read_study_document("test_document.txt")

    assert content == "Plants use sunlight for photosynthesis."
    assert error is None


def test_read_study_document_rejects_unsafe_path():
    """Unsafe document names should return an error."""
    content, error = app_module.read_study_document("../secret.txt")

    assert content is None
    assert error


def test_read_study_document_rejects_non_txt_file():
    """Only text documents should be accepted."""
    content, error = app_module.read_study_document("notes.pdf")

    assert content is None
    assert error


def test_read_study_document_missing_file(tmp_path, monkeypatch):
    """A missing local document should return an error."""
    monkeypatch.setattr(app_module, "STUDY_MATERIAL_DIR", tmp_path)
    monkeypatch.setattr(app_module, "BACKEND_MATERIAL_DIR", tmp_path)
    monkeypatch.setattr(app_module, "S3_BUCKET_NAME", "")
    monkeypatch.setattr(app_module, "s3_client", None)

    content, error = app_module.read_study_document("missing.txt")

    assert content is None
    assert error
def test_quiz_routes_require_authentication():
    """Quiz routes must reject requests without login."""
    client = app_module.app.test_client()

    requests = [
        ("GET", "/quiz-attempts"),
        ("POST", "/quizzes/generate"),
        ("GET", "/quizzes"),
        ("GET", "/quizzes/test-quiz-id"),
        ("POST", "/quizzes/test-quiz-id/attempt"),
    ]

    for method, path in requests:
        response = client.open(path, method=method)

        assert response.status_code in (401, 503), (
            f"{method} {path} should require authentication, "
            f"but returned {response.status_code}"
        )


