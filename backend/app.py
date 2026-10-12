import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client


# Load environment variables from backend/.env
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
STUDY_MATERIAL_DIR = PROJECT_DIR / "study_material"

load_dotenv(BACKEND_DIR / ".env")

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "null",
                "http://127.0.0.1:8000",
                "http://localhost:8000",
                "http://127.0.0.1:5500",
                "http://localhost:5500",
            ]
        }
    },
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv(
    "SUPABASE_SERVICE_ROLE_KEY", ""
)

supabase = None

if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    try:
        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_SERVICE_ROLE_KEY,
        )
        app.logger.info("Supabase connection configured.")
    except Exception:
        app.logger.exception("Could not configure Supabase.")


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "AI Study Assistant 2.0 backend is running"
    })


# Find available text documents in study_material.
@app.route("/documents", methods=["GET"])
def get_documents():
    try:
        STUDY_MATERIAL_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        documents = sorted(
            path.name
            for path in STUDY_MATERIAL_DIR.glob("*.txt")
            if path.is_file()
        )

        return jsonify({
            "documents": documents
        })

    except OSError:
        app.logger.exception("Could not list study documents.")

        return jsonify({
            "error": "Could not load study documents."
        }), 500


# Read one text document safely.
def read_study_document(document_name):
    if not isinstance(document_name, str):
        raise ValueError("Invalid document name.")

    if not document_name.strip():
        raise ValueError("Document name cannot be empty.")

    # Only accept a simple .txt filename, not a path.
    if (
        Path(document_name).name != document_name
        or "/" in document_name
        or "\\" in document_name
        or not document_name.lower().endswith(".txt")
    ):
        raise ValueError("Please select a valid .txt document.")

    document_path = STUDY_MATERIAL_DIR / document_name

    if not document_path.is_file():
        raise FileNotFoundError("The selected document was not found.")

    # Limit the document size to 1 MB for this beginner version.
    if document_path.stat().st_size > 1_000_000:
        raise ValueError(
            "This document is too large. Please use a text file smaller than 1 MB."
        )

    return document_path.read_text(encoding="utf-8")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}

    question = data.get("question", "")
    document_name = data.get("document")

    if not isinstance(question, str) or not question.strip():
        return jsonify({
            "error": "Please enter a question."
        }), 400

    if not OPENROUTER_API_KEY:
        return jsonify({
            "error": "OpenRouter API key is missing."
        }), 500

    # If a document is selected, use its text as context.
    document_context = ""

    if document_name:
        try:
            document_text = read_study_document(document_name)

            document_context = (
                "\n\nSelected study document: "
                + document_name
                + "\nDocument content:\n"
                + document_text
            )

        except FileNotFoundError:
            return jsonify({
                "error": "The selected study document was not found."
            }), 404

        except (ValueError, OSError, UnicodeError) as error:
            return jsonify({
                "error": str(error)
            }), 400

    system_message = (
        "You are a helpful AI study assistant. "
        "Explain answers in simple English for students. "
        "Give a clear answer with headings and bullet points when useful."
    )

    if document_context:
        system_message += (
            "\n\nThe user selected a study document. "
            "Use its contents as the main source when answering "
            "questions about that document. If the answer is not "
            "in the document, say so clearly. You may then provide "
            "general knowledge separately if helpful."
        )

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "nvidia/nemotron-3.5-lightning:free",
                "messages": [
                    {
                        "role": "system",
                        "content": system_message,
                    },
                    {
                        "role": "user",
                        "content": (
                            question.strip()
                            + document_context
                        ),
                    },
                ],
            },
            timeout=60,
        )

        if not response.ok:
            app.logger.error(
                "OpenRouter HTTP %s: %s",
                response.status_code,
                response.text,
            )

        response.raise_for_status()

        result = response.json()
        answer = result["choices"][0]["message"]["content"]

        if not isinstance(answer, str) or not answer.strip():
            app.logger.error("OpenRouter returned an empty answer.")

            return jsonify({
                "error": "The AI service returned an empty answer."
            }), 502

        # Save the question and answer to Supabase.
        if supabase is not None:
            try:
                supabase.table("study_history").insert({
                    "question": question.strip(),
                    "answer": answer,
                }).execute()

                app.logger.info(
                    "Study history saved to Supabase."
                )

            except Exception:
                app.logger.exception(
                    "Could not save study history to Supabase."
                )

        return jsonify({
            "answer": answer
        })

    except requests.exceptions.RequestException:
        app.logger.exception("OpenRouter request failed")

        return jsonify({
            "error": (
                "AI request failed. Check the backend log "
                "and verify that the free model is available."
            )
        }), 502

    except (KeyError, IndexError, TypeError, ValueError):
        app.logger.exception("Unexpected AI response")

        return jsonify({
            "error": "Unexpected response from the AI service."
        }), 502


@app.route("/history", methods=["GET"])
def get_history():
    if supabase is None:
        return jsonify({
            "error": "Supabase is not configured."
        }), 500

    try:
        result = (
            supabase.table("study_history")
            .select("id, question, answer, created_at")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        return jsonify({
            "history": result.data
        })

    except Exception:
        app.logger.exception(
            "Could not retrieve study history."
        )

        return jsonify({
            "error": "Could not load saved history from Supabase."
        }), 500


@app.route("/history/<int:question_id>", methods=["DELETE"])
def delete_history(question_id):
    if supabase is None:
        return jsonify({
            "error": "Supabase is not configured."
        }), 500

    try:
        result = (
            supabase.table("study_history")
            .delete()
            .eq("id", question_id)
            .execute()
        )

        if not result.data:
            return jsonify({
                "error": "Question not found."
            }), 404

        return jsonify({
            "message": "Question deleted successfully."
        })

    except Exception:
        app.logger.exception(
            "Could not delete study history."
        )

        return jsonify({
            "error": "Could not delete the saved question."
        }), 500


if __name__ == "__main__":
    app.run(debug=True)