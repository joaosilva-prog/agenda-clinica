"""Testes de integração: as páginas funcionando juntas, do formulário ao painel."""

from conftest import SENHA, pegar_csrf


def enviar(client, **campos):
    dados = {"nome": "Maria Souza", "telefone": "35998765432", "periodo": "tarde", "consentimento": "on", **campos}
    dados["csrf"] = pegar_csrf(client)
    return client.post("/solicitar", data=dados)


def test_pagina_inicial_abre(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "Solicitar horário" in resposta.get_data(as_text=True)


def test_health(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.get_json() == {"status": "ok"}


def test_health_avisa_quando_armazenamento_falha(client, repo, monkeypatch):
    monkeypatch.setattr(repo, "verificar", lambda: False)
    assert client.get("/health").status_code == 503


def test_solicitacao_valida_e_gravada(client, repo):
    resposta = enviar(client)
    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/obrigado")
    assert len(repo.listar()) == 1
    assert repo.listar()[0]["periodo"] == "tarde"
    assert client.get("/obrigado").status_code == 200


def test_solicitacao_invalida_mostra_erros_e_nao_grava(client, repo):
    resposta = enviar(client, telefone="123")
    assert resposta.status_code == 400
    assert "telefone com DDD" in resposta.get_data(as_text=True)
    assert repo.listar() == []


def test_post_sem_csrf_e_recusado(client, repo):
    resposta = client.post("/solicitar", data={"nome": "Maria", "telefone": "35998765432", "periodo": "manha"})
    assert resposta.status_code == 400
    assert repo.listar() == []


def test_painel_exige_login(client):
    resposta = client.get("/admin")
    assert resposta.status_code == 302
    assert "/admin/login" in resposta.headers["Location"]


def test_login_com_senha_errada(client):
    token = pegar_csrf(client, "/admin/login")
    resposta = client.post("/admin/login", data={"csrf": token, "usuario": "admin", "senha": "errada"})
    assert resposta.status_code == 401


def test_login_sem_senha_configurada_e_recusado(app, client):
    app.config["ADMIN_PASSWORD_HASH"] = ""
    token = pegar_csrf(client, "/admin/login")
    resposta = client.post("/admin/login", data={"csrf": token, "usuario": "admin", "senha": SENHA})
    assert resposta.status_code == 401


def test_painel_lista_solicitacoes(logado):
    enviar(logado, nome="Joana Lima")
    html = logado.get("/admin").get_data(as_text=True)
    assert "Joana Lima" in html
    assert "(35) 99876-5432" in html


def test_painel_vazio(logado):
    assert "Nenhuma solicitação" in logado.get("/admin").get_data(as_text=True)


def test_marcar_como_atendida(logado, repo):
    enviar(logado)
    chave = repo.listar()[0]["id"]
    token = pegar_csrf(logado, "/admin")
    resposta = logado.post(f"/admin/solicitacoes/{chave}/atendida", data={"csrf": token})
    assert resposta.status_code == 302
    assert repo.listar()[0]["atendida"] is True


def test_marcar_inexistente_da_404(logado):
    token = pegar_csrf(logado, "/admin")
    assert logado.post("/admin/solicitacoes/nao-existe/atendida", data={"csrf": token}).status_code == 404


def test_sair_encerra_a_sessao(logado):
    token = pegar_csrf(logado, "/admin")
    logado.post("/admin/sair", data={"csrf": token})
    assert logado.get("/admin").status_code == 302
