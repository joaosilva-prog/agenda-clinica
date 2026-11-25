import re

import pytest
from werkzeug.security import generate_password_hash

from clinica import create_app
from clinica.repositorio import RepositorioMemoria

SENHA = "senha-de-teste"


@pytest.fixture
def repo():
    return RepositorioMemoria()


@pytest.fixture
def app(repo):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "teste",
            "SESSION_COOKIE_SECURE": False,
            "ADMIN_USER": "admin",
            "ADMIN_PASSWORD_HASH": generate_password_hash(SENHA),
        },
        repositorio=repo,
    )


@pytest.fixture
def client(app):
    return app.test_client()


def pegar_csrf(client, caminho="/"):
    html = client.get(caminho).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


@pytest.fixture
def logado(client):
    token = pegar_csrf(client, "/admin/login")
    client.post("/admin/login", data={"csrf": token, "usuario": "admin", "senha": SENHA})
    return client
