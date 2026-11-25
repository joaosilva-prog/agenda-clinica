"""Onde as solicitações ficam guardadas.

- RepositorioDynamo: DynamoDB da AWS, usado em produção. Entra com a função
  (role) da Lambda, sem senha nem chave no código.
- RepositorioMemoria: usado nos testes e para rodar no computador.
"""

import uuid
from datetime import datetime, timezone

PARTICAO = "solicitacao"
_MAX_TS = 10**13


def _nova_chave() -> str:
    # Chave que ordena da mais nova para a mais antiga.
    agora_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return f"{_MAX_TS - agora_ms:013d}-{uuid.uuid4().hex[:8]}"


class RepositorioMemoria:
    def __init__(self):
        self._itens = {}

    def adicionar(self, dados: dict) -> str:
        chave = _nova_chave()
        self._itens[chave] = {
            **dados,
            "id": chave,
            "criado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "atendida": False,
        }
        return chave

    def listar(self) -> list[dict]:
        return [self._itens[k] for k in sorted(self._itens)]

    def marcar_atendida(self, chave: str) -> bool:
        if chave not in self._itens:
            return False
        self._itens[chave]["atendida"] = True
        return True

    def verificar(self) -> bool:
        return True


class RepositorioDynamo:  # pragma: no cover - depende da AWS
    """Guarda os pedidos no DynamoDB. Na Lambda, o boto3 entra sozinho com a
    função (role) da aplicação, sem chave nem senha no código."""

    def __init__(self, tabela: str):
        import boto3

        self._tabela = boto3.resource("dynamodb").Table(tabela)

    def adicionar(self, dados: dict) -> str:
        chave = _nova_chave()
        self._tabela.put_item(
            Item={
                "id": chave,
                **dados,
                "criado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "atendida": False,
            }
        )
        return chave

    def listar(self) -> list[dict]:
        itens = self._tabela.scan(Limit=500).get("Items", [])
        itens.sort(key=lambda i: i["id"])  # a chave já ordena do mais novo para o mais antigo
        return [
            {
                "id": i["id"],
                "nome": i.get("nome", ""),
                "telefone": i.get("telefone", ""),
                "periodo": i.get("periodo", ""),
                "criado_em": i.get("criado_em", ""),
                "atendida": bool(i.get("atendida", False)),
            }
            for i in itens[:200]
        ]

    def marcar_atendida(self, chave: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._tabela.update_item(
                Key={"id": chave},
                UpdateExpression="SET atendida = :sim",
                ConditionExpression="attribute_exists(id)",
                ExpressionAttributeValues={":sim": True},
            )
            return True
        except ClientError as erro:
            if erro.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def verificar(self) -> bool:
        try:
            self._tabela.reload()  # só consulta os dados da tabela, não gasta leitura
            return self._tabela.table_status == "ACTIVE"
        except Exception:
            return False
