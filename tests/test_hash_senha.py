"""O script de senha gera um hash que o painel aceita."""

from werkzeug.security import check_password_hash

from scripts.gerar_hash_senha import gerar_hash


def test_hash_gerado_e_aceito_pelo_login():
    h = gerar_hash("uma-senha-forte")
    assert check_password_hash(h, "uma-senha-forte")
    assert not check_password_hash(h, "outra-senha")
