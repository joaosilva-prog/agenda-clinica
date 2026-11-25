"""Testes unitários das regras do formulário."""

import pytest

from clinica.validacao import formatar_telefone, validar_solicitacao

VALIDO = {"nome": "Maria Souza", "telefone": "(35) 99876-5432", "periodo": "manha", "consentimento": "on"}


def test_solicitacao_valida_nao_tem_erros():
    dados, erros = validar_solicitacao(VALIDO)
    assert erros == []
    assert dados == {"nome": "Maria Souza", "telefone": "35998765432", "periodo": "manha"}


def test_remove_espacos_extras_do_nome():
    dados, _ = validar_solicitacao({**VALIDO, "nome": "  Maria   Souza "})
    assert dados["nome"] == "Maria Souza"


@pytest.mark.parametrize("nome", ["", "A", "x" * 101])
def test_nome_fora_do_tamanho(nome):
    _, erros = validar_solicitacao({**VALIDO, "nome": nome})
    assert any("nome" in e for e in erros)


@pytest.mark.parametrize("telefone", ["", "12345", "359987654321", "abc"])
def test_telefone_invalido(telefone):
    _, erros = validar_solicitacao({**VALIDO, "telefone": telefone})
    assert any("telefone" in e for e in erros)


@pytest.mark.parametrize("telefone", ["3537221234", "35 9 9876-5432"])
def test_telefone_fixo_e_celular_aceitos(telefone):
    _, erros = validar_solicitacao({**VALIDO, "telefone": telefone})
    assert erros == []


def test_periodo_desconhecido():
    _, erros = validar_solicitacao({**VALIDO, "periodo": "madrugada"})
    assert any("período" in e for e in erros)


def test_exige_consentimento():
    _, erros = validar_solicitacao({**VALIDO, "consentimento": None})
    assert any("autorizar" in e for e in erros)


def test_formulario_vazio_retorna_quatro_erros():
    _, erros = validar_solicitacao({})
    assert len(erros) == 4


@pytest.mark.parametrize(
    "entrada, esperado",
    [("35998765432", "(35) 99876-5432"), ("3537221234", "(35) 3722-1234"), ("123", "123")],
)
def test_formatar_telefone(entrada, esperado):
    assert formatar_telefone(entrada) == esperado
