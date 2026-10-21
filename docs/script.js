
const API_URL = "http://127.0.0.1:5000";

let accessToken = null;

async function apiRequest(endpoint, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (accessToken) {
        headers.Authorization = `Bearer ${accessToken}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.details || data.error || "Request failed.");
    }

    return data;
}

function showMessage(message) {
    const element = document.getElementById("message");

    if (element) {
        element.textContent = message;
    } else {
        alert(message);
    }
}

async function register() {
    const name = document.getElementById("name")?.value.trim();
    const email = document.getElementById("email")?.value.trim();
    const password = document.getElementById("password")?.value;

    if (!name || !email || !password) {
        showMessage("Please enter your name, email, and password.");
        return;
    }

    try {
        const data = await apiRequest("/auth/register", {
            method: "POST",
            body: JSON.stringify({
                display_name: name,
                email,
                password
            })
        });

        showMessage(
            data.message || "Registration submitted. Check your email to confirm your account."
        );
    } catch (error) {
        showMessage(error.message);
    }
}

async function login() {
    const email = document.getElementById("email")?.value.trim();
    const password = document.getElementById("password")?.value;

    if (!email || !password) {
        showMessage("Please enter your email and password.");
        return;
    }

    try {
        const data = await apiRequest("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password })
        });

        accessToken = data.access_token;

        showMessage("Login successful!");

        await loadHistory();
    } catch (error) {
        showMessage(error.message);
    }
}

async function askQuestion() {
    const question = document.getElementById("question")?.value.trim();
    const answerElement = document.getElementById("answer");

    if (!question) {
        showMessage("Please enter a question.");
        return;
    }

    if (answerElement) {
        answerElement.textContent = "Thinking...";
    }

    try {
        const data = await apiRequest("/ask", {
            method: "POST",
            body: JSON.stringify({ question })
        });

        if (answerElement) {
            answerElement.textContent = data.answer || "No answer received.";
        }

        showMessage("Answer received.");
    } catch (error) {
        if (answerElement) {
            answerElement.textContent = "Error: " + error.message;
        }
    }
}

async function loadHistory() {
    const historyElement = document.getElementById("history");

    if (!historyElement) {
        return;
    }

    if (!accessToken) {
        historyElement.textContent = "Please log in to view your history.";
        return;
    }

    try {
        const data = await apiRequest("/history");
        const records = Array.isArray(data.history)
            ? data.history
            : [];

        historyElement.replaceChildren();

        if (records.length === 0) {
            historyElement.textContent = "No saved questions yet.";
            return;
        }

        records.forEach((record) => {
            const item = document.createElement("article");
            const question = document.createElement("p");
            const answer = document.createElement("p");

            question.textContent = "Question: " + (record.question || "");
            answer.textContent = "Answer: " + (record.answer || "");

            item.append(question, answer);
            historyElement.appendChild(item);
        });
    } catch (error) {
        historyElement.textContent = "Could not load history: " + error.message;
    }
}

function logout() {
    accessToken = null;

    const historyElement = document.getElementById("history");

    if (historyElement) {
        historyElement.textContent = "Please log in to view your history.";
    }

    showMessage("You have logged out.");
}
