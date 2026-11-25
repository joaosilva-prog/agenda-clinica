"""Os pontos de entrada criam a aplicação sem erros, inclusive pela Lambda."""


def test_main_cria_aplicacao():
    import main

    assert main.app.test_client().get("/health").status_code == 200


def evento_http_api(caminho):
    """Evento no formato que o API Gateway (HTTP API, versão 2.0) entrega à Lambda."""
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": caminho,
        "rawQueryString": "",
        "headers": {"host": "exemplo.execute-api.us-east-2.amazonaws.com"},
        "requestContext": {
            "domainName": "exemplo.execute-api.us-east-2.amazonaws.com",
            "http": {"method": "GET", "path": caminho, "protocol": "HTTP/1.1", "sourceIp": "203.0.113.1"},
            "stage": "$default",
        },
        "isBase64Encoded": False,
    }


def test_handler_da_lambda_responde_health():
    import index

    resposta = index.handler(evento_http_api("/health"), None)
    assert resposta["statusCode"] == 200
    assert '"status":"ok"' in resposta["body"].replace(" ", "")


def test_handler_da_lambda_entrega_a_pagina_inicial():
    import index

    resposta = index.handler(evento_http_api("/"), None)
    assert resposta["statusCode"] == 200
    assert "Solicitar horário" in resposta["body"]
