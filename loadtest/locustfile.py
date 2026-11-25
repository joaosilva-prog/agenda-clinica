"""Teste de carga com Locust. Rodar na VM (IaaS):

    locust -f locustfile.py --headless -u 200 -r 20 -t 10m --host https://SEU-SITE

-u = usuários simultâneos, -r = quantos entram por segundo, -t = duração.
Só acessa a página inicial: não cria pedidos falsos no painel da clínica e não
consome o banco de dados (o /health consulta o DynamoDB).
"""

from locust import HttpUser, between, task


class Visitante(HttpUser):
    wait_time = between(1, 3)

    @task
    def pagina_inicial(self):
        self.client.get("/")
