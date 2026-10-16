
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

# =========================================================
# 1. CONFIGURATION
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parent
STUDY_MATERIAL_DIR = BACKEND_DIR / "study_material"

load_dotenv(BACKEND_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "nvidia/nemotron-3.5-lightning:free",
)

app = Flask(__name__)
CORS(app)

# =========================================================
# 2. GENERAL HELPERS
# =========================================================

def error_response(message, status=400):
    return jsonify({"error": message}), status


def get_json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def supabase_headers(access_token=None):
    headers = {"Content-Type": "application/json"}

    if SUPABASE_ANON_KEY:
        headers["apikey"] = SUPABASE_ANON_KEY

    token = access_token or SUPABASE_ANON_KEY

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


def get_access_token():
    authorization = request.headers.get("Authorization", "")

    if authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        return token or None

    return None


def get_current_user():
    token = get_access_token()

    if not token or not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return None

    try:
        response = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers=supabase_headers(token),
            timeout=15,
        )

        if response.status_code != 200:
            return None

        user = response.json()

        return (
            user
            if isinstance(user, dict) and user.get("id")
            else None
        )

    except (requests.RequestException, ValueError):
        app.logger.exception("Could not verify Supabase user.")
        return None


def supabase_rest_request(
    method,
    endpoint,
    access_token,
    params=None,
    json_body=None,
    extra_headers=None,
):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("Supabase configuration is missing.")

    headers = supabase_headers(access_token)

    if extra_headers:
        headers.update(extra_headers)

    return requests.request(
        method=method,
        url=f"{SUPABASE_URL}/rest/v1/{endpoint}",
        headers=headers,
        params=params,
        json=json_body,
        timeout=20,
    )


def supabase_error_message(result, fallback):
    if not isinstance(result, dict):
        return fallback

    return (
        result.get("msg")
        or result.get("message")
        or result.get("error_description")
        or result.get("error")
        or fallback
    )


# =========================================================
# 3. HOME
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "AI Study Assistant 2.0 backend is running"
    }), 200


# =========================================================
# 4. REGISTER
# =========================================================

@app.route("/auth/register", methods=["POST"])
def register():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return error_response(
            "Supabase configuration is missing in backend/.env.",
            500,
        )

    data = get_json_body()

    email = str(data.get("email", "")).strip()
    password = data.get("password", "")

    if not email or not isinstance(password, str) or not password:
        return error_response("Email and password are required.")

    if len(password) < 6:
        return error_response(
            "Password must contain at least 6 characters."
        )

    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            headers=supabase_headers(),
            json={"email": email, "password": password},
            timeout=20,
        )

        try:
            result = response.json()
        except ValueError:
            result = {}

        if response.status_code not in (200, 201):
            return error_response(
                supabase_error_message(
                    result,
                    "Registration failed.",
                ),
                response.status_code,
            )

        access_token = result.get("access_token")
        existing_session = result.get("session")

        if isinstance(existing_session, dict):
            access_token = (
                existing_session.get("access_token")
                or access_token
            )
        else:
            existing_session = {}

        session = None

        if access_token:
            session = {
                "access_token": access_token,
                "refresh_token": (
                    result.get("refresh_token")
                    or existing_session.get("refresh_token")
                ),
                "token_type": (
                    result.get("token_type")
                    or existing_session.get("token_type")
                ),
                "expires_in": (
                    result.get("expires_in")
                    or existing_session.get("expires_in")
                ),
                "expires_at": (
                    result.get("expires_at")
                    or existing_session.get("expires_at")
                ),
            }

        return jsonify({
            "message": (
                "Registration successful. You can log in now. "
                "If email confirmation is enabled, confirm your "
                "email first."
            ),
            "user": result.get("user"),
            "session": session,
        }), 200

    except requests.Timeout:
        return error_response(
            "Supabase registration request timed out. Please try again.",
            504,
        )

    except requests.RequestException:
        app.logger.exception("Registration request failed.")

        return error_response(
            "Could not connect to Supabase to register.",
            502,
        )


# =========================================================
# 5. LOGIN
# =========================================================

@app.route("/auth/login", methods=["POST"])
def login():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return error_response(
            "Supabase configuration is missing in backend/.env.",
            500,
        )

    data = get_json_body()

    email = str(data.get("email", "")).strip()
    password = data.get("password", "")

    if not email or not isinstance(password, str) or not password:
        return error_response("Email and password are required.")

    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token",
            params={"grant_type": "password"},
            headers=supabase_headers(),
            json={"email": email, "password": password},
            timeout=20,
        )

        try:
            result = response.json()
        except ValueError:
            result = {}

        if response.status_code != 200:
            message = supabase_error_message(
                result,
                "Login failed. Check your email and password.",
            )

            app.logger.warning(
                "Supabase login failed with HTTP status %s: %s",
                response.status_code,
                message,
            )

            return error_response(message, response.status_code)

        session_data = result.get("session")

        if not isinstance(session_data, dict):
            session_data = {}

        access_token = (
            result.get("access_token")
            or session_data.get("access_token")
        )

        if not access_token:
            app.logger.error(
                "Supabase returned HTTP 200 for login but no "
                "access_token. Response keys: %s",
                list(result.keys()),
            )

            return error_response(
                "Supabase accepted the login request but returned "
                "no access token. Check the Flask terminal for the "
                "response keys and verify the Supabase Auth configuration.",
                502,
            )

        session = {
            "access_token": access_token,
            "refresh_token": (
                result.get("refresh_token")
                or session_data.get("refresh_token")
            ),
            "token_type": (
                result.get("token_type")
                or session_data.get("token_type")
            ),
            "expires_in": (
                result.get("expires_in")
                or session_data.get("expires_in")
            ),
            "expires_at": (
                result.get("expires_at")
                or session_data.get("expires_at")
            ),
        }

        return jsonify({
            "message": "Login successful!",
            "user": result.get("user"),
            "session": session,
        }), 200

    except requests.Timeout:
        return error_response(
            "Supabase login request timed out. Please try again.",
            504,
        )

    except requests.RequestException:
        app.logger.exception("Login request failed.")

        return error_response(
            "Could not connect to Supabase to log in.",
            502,
        )


# =========================================================
# 6. CURRENT USER
# =========================================================

@app.route("/auth/me", methods=["GET"])
def current_user():
    user = get_current_user()

    if not user:
        return error_response(
            "Your session is invalid or expired. Please log in again.",
            401,
        )

    return jsonify({"user": user}), 200


# =========================================================
# 7. LIST STUDY DOCUMENTS
# =========================================================

@app.route("/documents", methods=["GET"])
def documents():
    if not STUDY_MATERIAL_DIR.is_dir():
        app.logger.warning(
            "Study material folder not found: %s",
            STUDY_MATERIAL_DIR,
        )

        return jsonify({"documents": []}), 200

    document_list = [
        {"name": path.name}
        for path in sorted(STUDY_MATERIAL_DIR.glob("*.txt"))
        if path.is_file()
    ]

    return jsonify({"documents": document_list}), 200


# =========================================================
# 8. READ A SELECTED STUDY DOCUMENT
# =========================================================

def read_study_document(document_name):
    """Safely read a .txt document from the study materials folder."""

    if (
        not isinstance(document_name, str)
        or not document_name.strip()
    ):
        raise ValueError("Invalid document name.")

    name = document_name.strip()

    # Reject paths that try to access another folder.
    if "/" in name or "\\" in name or Path(name).name != name:
        raise ValueError("Document paths are not allowed.")

    # Accept a filename with .txt or a name without an extension.
    suffix = Path(name).suffix

    if suffix:
        if suffix.lower() != ".txt":
            raise ValueError("Only .txt documents are allowed.")

        filename = name
    else:
        filename = f"{name}.txt"

    base_dir = STUDY_MATERIAL_DIR.resolve()
    file_path = (base_dir / filename).resolve()

    # Make sure the resolved path stays inside the study folder.
    try:
        file_path.relative_to(base_dir)
    except ValueError:
        raise ValueError("Document path is not allowed.")

    # Missing documents must raise FileNotFoundError.
    if not file_path.is_file():
        raise FileNotFoundError(
            f"Study document not found: {filename}"
        )

    # Read up to 15,000 characters, supporting UTF-8 text files.
    with file_path.open("r", encoding="utf-8-sig") as file:
        return file.read(15000)


# =========================================================
# 9. ASK AI
# =========================================================

@app.route("/ask", methods=["POST"])
def ask():
    data = get_json_body()

    # Validate the question before contacting OpenRouter.
    question_value = data.get("question")

    if not isinstance(question_value, str):
        return error_response("Please enter a question.")

    question = question_value.strip()

    if not question:
        return error_response("Please enter a question.")

    if len(question) > 5000:
        return error_response(
            "Your question is too long. Please shorten it."
        )

    document_name = (
        data.get("document")
        or data.get("document_name")
        or data.get("selected_document")
        or ""
    )

    if document_name and not isinstance(document_name, str):
        return error_response(
            "The selected document name is invalid."
        )

    if not OPENROUTER_API_KEY:
        return error_response(
            "OPENROUTER_API_KEY is missing from backend/.env.",
            500,
        )

    document_text = None

    if document_name:
        try:
            document_text = read_study_document(document_name)
        except ValueError:
            return error_response(
                "The selected document name or file type is invalid."
            )
        except FileNotFoundError:
            return error_response(
                "The selected study document could not be found. "
                "Check its filename and location.",
                404,
            )
        except (OSError, UnicodeError):
            app.logger.exception(
                "Could not read selected study document."
            )

            return error_response(
                "The selected study document could not be read.",
                500,
            )

    if document_text:
        system_prompt = (
            "You are a helpful student study assistant. "
            "Use simple, clear English. "
            "The student selected a study document. "
            "Use that document as the primary source. "
            "Do not invent information or claim something is in "
            "the document if it is not. "
            "If the document does not contain the answer, "
            "say so clearly."
        )

        user_prompt = (
            f"Selected document: {document_name}\n\n"
            f"DOCUMENT CONTENT:\n{document_text}\n\n"
            f"STUDENT QUESTION:\n{question}\n\n"
            "Answer using the selected document."
        )

    else:
        system_prompt = (
            "You are a helpful student study assistant. "
            "Answer in simple, clear English. "
            "Use examples when helpful."
        )

        user_prompt = question

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://127.0.0.1:5000",
                "X-Title": "AI Study Assistant 2.0",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            },
            timeout=90,
        )

        try:
            result = response.json()
        except ValueError:
            result = {}

        if response.status_code != 200:
            app.logger.error(
                "OpenRouter request failed with status %s.",
                response.status_code,
            )

            api_error = (
                result.get("error", {})
                if isinstance(result, dict)
                else {}
            )

            message = (
                api_error.get("message")
                if isinstance(api_error, dict)
                else None
            )

            return error_response(
                message or "The AI service could not answer right now.",
                502,
            )

        choices = (
            result.get("choices", [])
            if isinstance(result, dict)
            else []
        )

        if not choices:
            return error_response(
                "The AI returned no answer. Please try again.",
                502,
            )

        answer = choices[0].get("message", {}).get("content", "")

        if not isinstance(answer, str) or not answer.strip():
            return error_response(
                "The AI returned an empty answer. Please try again.",
                502,
            )

        answer = answer.strip()

    except requests.Timeout:
        return error_response(
            "The AI service took too long to respond. Try again.",
            504,
        )

    except requests.RequestException:
        app.logger.exception("AI request failed.")

        return error_response(
            "Could not connect to the AI service.",
            502,
        )

    # Save history only when a valid user session is supplied.
    user = get_current_user()

    if user:
        try:
            save_response = supabase_rest_request(
                "POST",
                "study_history",
                get_access_token(),
                json_body={
                    "user_id": user["id"],
                    "question": question,
                    "answer": answer,
                },
                extra_headers={"Prefer": "return=minimal"},
            )

            if save_response.status_code not in (200, 201, 204):
                app.logger.error(
                    "History save failed with status %s.",
                    save_response.status_code,
                )

        except (requests.RequestException, RuntimeError):
            app.logger.exception(
                "Could not save question history."
            )

    return jsonify({"answer": answer}), 200


# =========================================================
# 10. GET SAVED HISTORY
# =========================================================

@app.route("/history", methods=["GET"])
def history():
    user = get_current_user()

    if not user:
        return error_response(
            "Please log in to view your question history.",
            401,
        )

    try:
        response = supabase_rest_request(
            "GET",
            "study_history",
            get_access_token(),
            params={
                "select": "id,question,answer,created_at",
                "user_id": f"eq.{user['id']}",
                "order": "created_at.desc",
            },
        )

        if response.status_code != 200:
            app.logger.error(
                "History request failed with status %s.",
                response.status_code,
            )

            return error_response(
                "Could not load history. Check your Supabase table "
                "and Row Level Security policies.",
                502,
            )

        return jsonify({"history": response.json()}), 200

    except (requests.RequestException, ValueError, RuntimeError):
        app.logger.exception(
            "Could not retrieve question history."
        )

        return error_response(
            "Could not connect to Supabase to load history.",
            502,
        )


# =========================================================
# 11. DELETE SAVED HISTORY
# =========================================================

@app.route("/history/<int:question_id>", methods=["DELETE"])
def delete_history(question_id):
    user = get_current_user()

    if not user:
        return error_response(
            "Please log in to delete saved questions.",
            401,
        )

    try:
        response = supabase_rest_request(
            "DELETE",
            "study_history",
            get_access_token(),
            params={
                "id": f"eq.{question_id}",
                "user_id": f"eq.{user['id']}",
            },
            extra_headers={"Prefer": "return=minimal"},
        )

        if response.status_code not in (200, 204):
            app.logger.error(
                "History deletion failed with status %s.",
                response.status_code,
            )

            return error_response(
                "Could not delete the question. Check your Supabase "
                "table and Row Level Security policies.",
                502,
            )

        return jsonify({
            "message": "Question deleted successfully."
        }), 200

    except (requests.RequestException, RuntimeError):
        app.logger.exception(
            "Could not delete question history."
        )

        return error_response(
            "Could not connect to Supabase to delete the question.",
            502,
        )


# =========================================================
# 12. START FLASK
# =========================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
