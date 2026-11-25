"""Regras de validação do formulário de solicitação de horário.

O formulário pede só o mínimo para a clínica retornar o contato.
Nenhuma informação clínica é coletada (LGPD: minimização de dados).
"""

import re

PERIODOS = {"manha": "Manhã", "tarde": "Tarde"}


def so_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def validar_solicitacao(dados: dict) -> tuple[dict, list[str]]:
    """Recebe os campos do formulário e devolve (dados_limpos, erros)."""
    erros = []

    nome = " ".join((dados.get("nome") or "").split())
    if not 2 <= len(nome) <= 100:
        erros.append("Informe o nome do responsável (de 2 a 100 caracteres).")

    telefone = so_digitos(dados.get("telefone", ""))
    if len(telefone) not in (10, 11):
        erros.append("Informe um telefone com DDD (10 ou 11 dígitos).")

    periodo = dados.get("periodo", "")
    if periodo not in PERIODOS:
        erros.append("Escolha o período de preferência.")

    if dados.get("consentimento") != "on":
        erros.append("É preciso autorizar o uso dos dados para o contato.")

    limpos = {"nome": nome, "telefone": telefone, "periodo": periodo}
    return limpos, erros


def formatar_telefone(telefone: str) -> str:
    """11987654321 -> (11) 98765-4321"""
    t = so_digitos(telefone)
    if len(t) == 11:
        return f"({t[:2]}) {t[2:7]}-{t[7:]}"
    if len(t) == 10:
        return f"({t[:2]}) {t[2:6]}-{t[6:]}"
    return telefone
