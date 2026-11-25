"""Agenda Online da clínica: site com pedido de horário e painel da equipe."""

import os
import secrets
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .repositorio import RepositorioDynamo, RepositorioMemoria
from .validacao import PERIODOS, formatar_telefone, validar_solicitacao


def _criar_repositorio():
    if os.getenv("ARMAZENAMENTO") == "dynamodb":  # pragma: no cover - só na AWS
        return RepositorioDynamo(os.environ["TABELA"])
    return RepositorioMemoria()


def create_app(config: dict | None = None, repositorio=None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
        ADMIN_USER=os.getenv("ADMIN_USER", "admin"),
        ADMIN_PASSWORD_HASH=os.getenv("ADMIN_PASSWORD_HASH", ""),
        CLINICA_NOME=os.getenv("CLINICA_NOME", "Clínica de Psicologia Infantil"),
        CLINICA_CIDADE=os.getenv("CLINICA_CIDADE", "Poços de Caldas, MG"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "true") == "true",
    )
    if config:
        app.config.update(config)

    repo = repositorio or _criar_repositorio()
    app.extensions["repositorio"] = repo

    # ---------- proteção contra envio de formulário por outro site (CSRF)
    def token_csrf() -> str:
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    @app.before_request
    def conferir_csrf():
        if request.method == "POST":
            enviado = request.form.get("csrf", "")
            if not enviado or not secrets.compare_digest(enviado, session.get("csrf", "")):
                abort(400)

    @app.context_processor
    def variaveis_globais():
        return {
            "csrf": token_csrf,
            "clinica": app.config["CLINICA_NOME"],
            "cidade": app.config["CLINICA_CIDADE"],
            "periodos": PERIODOS,
        }

    app.jinja_env.filters["telefone"] = formatar_telefone

    def exige_login(view):
        @wraps(view)
        def protegida(*args, **kwargs):
            if not session.get("admin"):
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return protegida

    # ---------- área pública
    @app.get("/")
    def inicio():
        return render_template("inicio.html", dados={}, erros=[])

    @app.post("/solicitar")
    def solicitar():
        dados, erros = validar_solicitacao(request.form)
        if erros:
            return render_template("inicio.html", dados=dados, erros=erros), 400
        repo.adicionar(dados)
        return redirect(url_for("obrigado"))

    @app.get("/obrigado")
    def obrigado():
        return render_template("obrigado.html")

    @app.get("/health")
    def health():
        if repo.verificar():
            return {"status": "ok"}
        return {"status": "erro"}, 503

    # ---------- painel da equipe
    @app.route("/admin/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            usuario_ok = request.form.get("usuario") == app.config["ADMIN_USER"]
            senha_hash = app.config["ADMIN_PASSWORD_HASH"]
            senha_ok = bool(senha_hash) and check_password_hash(senha_hash, request.form.get("senha", ""))
            if usuario_ok and senha_ok:
                session.clear()
                session["admin"] = True
                return redirect(url_for("painel"))
            return render_template("login.html", erro="Usuário ou senha inválidos."), 401
        return render_template("login.html", erro=None)

    @app.post("/admin/sair")
    def sair():
        session.clear()
        return redirect(url_for("inicio"))

    @app.get("/admin")
    @exige_login
    def painel():
        return render_template("painel.html", solicitacoes=repo.listar())

    @app.post("/admin/solicitacoes/<chave>/atendida")
    @exige_login
    def marcar_atendida(chave):
        if repo.marcar_atendida(chave):
            flash("Solicitação marcada como atendida.")
        else:
            abort(404)
        return redirect(url_for("painel"))

    return app
