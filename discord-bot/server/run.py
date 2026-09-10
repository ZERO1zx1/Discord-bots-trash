"""Development entry point for the Flask process."""

from dotenv import load_dotenv

from server.guildpilot import create_app

load_dotenv()
app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

