"""Gera o hash da senha do painel, no formato que o Flask/Werkzeug confere.

Uso (no Cloud Shell ou no seu computador, só precisa de Python):
    python3 scripts/gerar_hash_senha.py

A senha não aparece na tela e não fica salva em lugar nenhum.
"""

import getpass
import hashlib
import secrets

ITERACOES = 600_000


def gerar_hash(senha: str) -> str:
    sal = secrets.token_hex(8)
    resumo = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), ITERACOES).hex()
    return f"pbkdf2:sha256:{ITERACOES}${sal}${resumo}"


if __name__ == "__main__":  # pragma: no cover
    senha = getpass.getpass("Senha do painel: ")
    if len(senha) < 10:
        raise SystemExit("Use uma senha com pelo menos 10 caracteres.")
    print(gerar_hash(senha))
