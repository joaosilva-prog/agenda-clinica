"""Roda a aplicação no seu computador: python main.py"""

from clinica import create_app

app = create_app()

if __name__ == "__main__":  # pragma: no cover - execução local
    app.config["SESSION_COOKIE_SECURE"] = False
    app.run(debug=True)
