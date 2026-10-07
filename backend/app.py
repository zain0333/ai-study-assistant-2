from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return {"message": "AI Study Assistant 2.0 backend is running"}


if __name__ == "__main__":
    app.run(debug=True)