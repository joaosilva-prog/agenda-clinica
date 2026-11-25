"""Ponto de entrada da AWS Lambda (handler: index.handler).

O API Gateway entrega cada requisição HTTP como um evento; o apig-wsgi
converte esse evento para o Flask e a resposta de volta.
"""

import os


def _carregar_segredos():  # pragma: no cover - só na AWS
    """Lê a chave de sessão e o hash da senha do Parameter Store (criptografados)."""
    import boto3

    prefixo = os.environ["SSM_PREFIXO"]
    nomes = {f"{prefixo}secret-key": "SECRET_KEY", f"{prefixo}admin-password-hash": "ADMIN_PASSWORD_HASH"}
    resposta = boto3.client("ssm").get_parameters(Names=list(nomes), WithDecryption=True)
    for parametro in resposta["Parameters"]:
        os.environ[nomes[parametro["Name"]]] = parametro["Value"]


if os.getenv("SSM_PREFIXO"):  # pragma: no cover - só na AWS
    _carregar_segredos()

from apig_wsgi import make_lambda_handler  # noqa: E402

from clinica import create_app  # noqa: E402

app = create_app()
handler = make_lambda_handler(app)
