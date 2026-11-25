# Agenda Online da clínica

Site simples de uma clínica de psicologia infantil, hospedado na AWS.

- **Área pública:** o responsável deixa nome, telefone e período de preferência. A clínica retorna para marcar o horário.
- **Painel da clínica:** com usuário e senha, a equipe vê os pedidos e marca os que já foram atendidos.

O formulário **não pede nenhuma informação de saúde da criança**. Isso segue a LGPD (minimização de dados) e é importante por ser uma clínica de psicologia infantil.

## O que tem em cada pasta

| Caminho | O que é |
| --- | --- |
| `clinica/` | A aplicação (Python + Flask) |
| `index.py` | Ponto de entrada na AWS Lambda |
| `main.py` | Para rodar no seu computador |
| `tests/` | 35 testes automatizados (unitários e de integração) |
| `infra/template.yaml` | Toda a infraestrutura da AWS em código (CloudFormation) |
| `.github/workflows/ci-cd.yml` | Pipeline: lint, testes, publicação e teste de fumaça |
| `loadtest/locustfile.py` | Teste de carga, para rodar na máquina virtual |
| `scripts/gerar_hash_senha.py` | Gera o hash da senha do painel |

## Arquitetura

| Recurso | Serviço da AWS | Modelo | Para quê |
| --- | --- | --- | --- |
| Entrada HTTPS | API Gateway (HTTP API) | PaaS | Recebe as requisições com HTTPS e entrega para a aplicação |
| Aplicação | AWS Lambda | PaaS (serverless) | Roda o Flask; escala sozinha conforme o número de acessos |
| Banco de dados | DynamoDB | PaaS | Guarda os pedidos; criptografado; acesso só pela função da aplicação |
| Segredos | Systems Manager Parameter Store | PaaS | Senha do painel e chave de sessão, criptografadas e fora do código |
| Monitoramento | CloudWatch (painel, logs e 3 alarmes) + SNS | PaaS | Métricas, logs e alertas por e-mail |
| Máquina virtual | EC2 (t3.micro, Ubuntu) | IaaS | Roda o teste de carga |
| Identidade do GitHub | IAM + OpenID Connect | — | O pipeline publica sem nenhuma chave guardada |

---

# Guia de configuração, passo a passo

Faça na ordem. Onde estiver `SEU-USUARIO`, `SEU-EMAIL` etc., troque pelos valores de vocês.

## 1. Conferir a conta e a região

1. A conta precisa estar no **Plano gratuito** (*Free plan*). Nesse plano a AWS não cobra nada: o uso sai dos créditos e, se eles acabarem, a conta é encerrada em vez de cobrar. **Nunca clique em "Upgrade plan".**
2. Veja a região da conta. Para contas do Brasil no cadastro novo, ela é **US East (Ohio), `us-east-2`**. Confirme em https://settings.aws.com → **Project** → **Additional info** → **Region**, ou no canto superior direito do console. Use essa região em todos os passos.
3. Segurança: ative o MFA (verificação em duas etapas) no seu usuário principal: menu com o seu nome no canto superior direito → **Credenciais de segurança** → **Atribuir dispositivo de MFA**.

## 2. Criar o repositório no GitHub

1. No GitHub, **New repository** → nome `agenda-clinica` → **Public** (não há nenhuma senha no código) → **Create repository**.
2. No terminal do seu computador, dentro da pasta do projeto:

   ```bash
   git init
   git add .
   git commit -m "Primeira versão da agenda da clínica"
   git branch -M main
   git remote add origin https://github.com/SEU-USUARIO/agenda-clinica.git
   git push -u origin main
   ```

   O pipeline roda nesse primeiro push. **Lint e testes** deve ficar verde. **Publicar na AWS** vai falhar agora, porque a infraestrutura ainda não existe. Isso é esperado.

## 3. Criar toda a infraestrutura (CloudShell)

1. No console da AWS, clique no ícone do **CloudShell** (`>_`, na barra do topo). Um terminal abre embaixo, já logado na sua conta.
2. Baixe o projeto:

   ```bash
   git clone https://github.com/SEU-USUARIO/agenda-clinica.git
   cd agenda-clinica
   ```

3. Guarde os dois segredos no Parameter Store, criptografados. O primeiro comando pede a senha do painel (mínimo de 10 caracteres) sem mostrar na tela:

   ```bash
   HASH="$(python3 scripts/gerar_hash_senha.py)"
   aws ssm put-parameter --name /agenda-clinica/admin-password-hash --type SecureString --value "$HASH"
   aws ssm put-parameter --name /agenda-clinica/secret-key --type SecureString --value "$(openssl rand -hex 32)"
   ```

4. Crie tudo com um comando (troque os 3 valores):

   ```bash
   aws cloudformation deploy \
     --stack-name agenda-clinica \
     --template-file infra/template.yaml \
     --capabilities CAPABILITY_NAMED_IAM \
     --parameter-overrides \
       GitHubRepo=SEU-USUARIO/agenda-clinica \
       ClinicaNome="NOME DA CLÍNICA" \
       EmailAlertas=SEU-EMAIL@exemplo.com
   ```

   Leva de 2 a 4 minutos e termina com `Successfully created/updated stack`. O que ele cria: a tabela do DynamoDB, a função Lambda, a API HTTPS, as 2 funções (roles) do IAM com o mínimo de permissão, a ligação segura com o GitHub, o painel e os 3 alarmes do CloudWatch e o tópico de e-mail.

5. Veja os valores que você vai usar no passo 4:

   ```bash
   aws cloudformation describe-stacks --stack-name agenda-clinica \
     --query "Stacks[0].Outputs[].[Description,OutputValue]" --output table
   ```

6. Abra seu e-mail e clique em **Confirm subscription** na mensagem *AWS Notification - Subscription Confirmation*. Sem isso, os alarmes não chegam.

**Se der erro:**
- *"...oidc-provider/token.actions.githubusercontent.com already exists"*: a conta já tem a ligação com o GitHub. Repita o comando do item 4 acrescentando `CriarProvedorGitHub=nao` depois do e-mail.
- *Status `ROLLBACK_COMPLETE`*: apague a tentativa com `aws cloudformation delete-stack --stack-name agenda-clinica`, espere 1 minuto e repita o item 4.
- Qualquer outro erro: rode `aws cloudformation describe-stack-events --stack-name agenda-clinica --query "StackEvents[?ResourceStatus=='CREATE_FAILED'].[LogicalResourceId,ResourceStatusReason]" --output table` e me mande o resultado.

## 4. Ligar o GitHub à AWS

1. No repositório: **Settings → Secrets and variables → Actions → aba Variables → New repository variable**. Crie as 4 variáveis com os valores do passo 3 (o nome de cada uma aparece na descrição da tabela):
   - `AWS_REGION`
   - `AWS_DEPLOY_ROLE_ARN`
   - `AWS_LAMBDA_FUNCTION`
   - `AWS_API_URL`

   Não precisa de nenhum *secret*: o GitHub entra na AWS sem chave, por OpenID Connect.
2. Vá em **Actions → CI/CD → Run workflow** (branch `main`). Em uns 2 minutos as duas etapas ficam verdes. A última, **Teste de fumaça**, confirma que o site está no ar.
3. Abra o endereço de `AWS_API_URL`. Faça um pedido de teste e depois entre em `/admin/login` com o usuário `admin` e a senha do passo 3.

## 5. Proteger o branch principal (qualidade)

1. **Settings → Collaborators → Add people**: adicione a Eduarda.
2. **Settings → Branches → Add branch ruleset**:
   - Nome: `proteger-main`; **Enforcement status**: *Active*; **Target branches**: *Include default branch*.
   - Marque **Require a pull request before merging**, com **Required approvals = 1**.
   - Marque **Require status checks to pass** e adicione o check **Lint e testes**.
   - Marque **Block force pushes** → **Create**.

A partir daí, toda mudança entra por pull request, revisada pela outra pessoa, e só depois que os testes passarem.

## 6. Permissões na AWS (IAM)

1. Console → **IAM → Usuários → Criar usuário**. Nome: `eduarda`. Marque **Fornecer acesso ao console**, com senha personalizada. Em permissões, escolha **Anexar políticas diretamente** → **ReadOnlyAccess** → **Criar usuário**. Mande para ela o link de login e a senha que aparecem no fim. Ela vê tudo, mas não altera nada: as mudanças entram pelo GitHub.
2. Em **IAM → Funções**, confira as duas que o CloudFormation criou:
   - `agenda-clinica-lambda`: é com ela que a aplicação roda. Só pode gravar logs, usar a tabela `agenda-solicitacoes` e ler os 2 parâmetros `/agenda-clinica/*`.
   - `agenda-clinica-github-deploy`: é a que o pipeline usa. Só aceita o branch `main` do seu repositório e só pode atualizar o código da função `agenda-clinica`.

## 7. Domínio próprio com HTTPS

1. **Certificate Manager (ACM)**, na região da conta → **Solicitar** → **Solicitar um certificado público**. Nome de domínio: `agenda.seudominio.com.br`. Validação: **DNS** → **Solicitar**.
2. Abra o certificado e copie o registro **CNAME** de validação (nome e valor). Crie esse CNAME no DNS do domínio (no Registro.br: **Domínios → seu domínio → DNS → Editar zona → Nova entrada**). Em alguns minutos o certificado fica **Emitido**.
3. **API Gateway → Nomes de domínio personalizados → Criar**. Domínio: `agenda.seudominio.com.br`; tipo de endpoint: **Regional**; certificado: o do item 1 → **Criar**.
4. Na aba **Mapeamentos de API** → **Configurar mapeamentos de API** → **Adicionar novo mapeamento**: API `agenda-clinica`, estágio `$default` → **Salvar**.
5. Copie o **Nome de domínio do API Gateway** (algo como `d-abc123.execute-api.us-east-2.amazonaws.com`) e crie no DNS:

   | Tipo | Nome | Valor |
   | --- | --- | --- |
   | CNAME | `agenda` | `d-abc123.execute-api.us-east-2.amazonaws.com` |

6. Depois que o DNS propagar, teste `https://agenda.seudominio.com.br`.

> Se a clínica ainda não tiver domínio, dá para registrar um `.com.br` no https://registro.br. É o único custo possível do projeto, e é fora da AWS.

## 8. Teste de carga em uma máquina virtual (IaaS)

1. Console → **EC2 → Executar instância**:
   - **Nome:** `vm-teste-carga`
   - **Imagem:** Ubuntu Server 24.04 LTS (*Qualificado para o nível gratuito*)
   - **Tipo:** `t3.micro` (*Qualificado para o nível gratuito*)
   - **Par de chaves:** *Prosseguir sem um par de chaves* (o acesso será pelo navegador, com chave temporária)
   - **Configurações de rede:** criar grupo de segurança permitindo **SSH**
   - **Armazenamento:** 8 GiB gp3 (o padrão)
   - **Executar instância**.
2. Selecione a VM → **Conectar** → aba **EC2 Instance Connect** → **Conectar**. Abre um terminal no navegador. Rode:

   ```bash
   sudo apt update && sudo apt install -y python3-venv
   python3 -m venv locust && . locust/bin/activate && pip install locust
   curl -O https://raw.githubusercontent.com/SEU-USUARIO/agenda-clinica/main/loadtest/locustfile.py
   locust -f locustfile.py --headless -u 50 -r 10 -t 5m --host ENDERECO-DO-SITE
   ```

3. Enquanto roda, abra **CloudWatch → Painéis → agenda-clinica** e veja **Execuções simultâneas (escala)** subir: a Lambda cria novas cópias da aplicação sozinha conforme a carga e volta a zero quando ela acaba. Veja também o tempo de resposta e as requisições por minuto.
   - Contas novas da AWS começam com um limite baixo de execuções simultâneas na Lambda, que a AWS aumenta com o uso. Se aparecerem limitações (*Throttles*) no painel, isso mostra o limite de escala da conta. Vale citar no trabalho.
4. **Encerre a VM** quando terminar: selecione → **Estado da instância → Encerrar (excluir)**.

## 9. Monitoramento

- **CloudWatch → Painéis → agenda-clinica:** requisições, erros 4xx/5xx, tempo de resposta (p50 e p95), execuções simultâneas e limitações.
- **CloudWatch → Alarmes:** 3 alarmes que mandam e-mail: mais de 5 erros 5xx em 5 minutos, tempo de resposta p95 acima de 1 segundo e falhas ou limitações da Lambda.
- **CloudWatch → Grupos de logs → /aws/lambda/agenda-clinica:** cada requisição e cada erro da aplicação (guardados por 14 dias).
- **Lambda → agenda-clinica → Monitorar:** visão rápida de invocações, duração e erros.

## 10. Onde ver as métricas de qualidade

- **GitHub → Actions →** qualquer execução do CI/CD: o resumo mostra quantos testes rodaram, as falhas e a **cobertura de testes**. Os relatórios ficam em *Artifacts*.
- **Pull requests:** mostram a revisão da outra pessoa e o check **Lint e testes**.
- **CloudWatch:** tempo de resposta, taxa de erros e escala em produção.

## 11. Custo zero

A conta está no **Plano gratuito**: a AWS não cobra nada nesse plano. Além disso, quase tudo cabe no uso **sempre gratuito** da AWS:

| Serviço | Uso sempre gratuito | Uso no projeto |
| --- | --- | --- |
| Lambda | 1 milhão de requisições por mês | Poucos milhares, mais o teste de carga |
| DynamoDB | 25 GB e 25 unidades de leitura/escrita | Poucos pedidos; tabela com 5/5 |
| CloudWatch | 10 alarmes, 3 painéis, 5 GB de logs | 3 alarmes, 1 painel, logs por 14 dias |
| SNS | 1.000 e-mails por mês | Só quando um alarme dispara |
| Parameter Store e Certificate Manager | Parâmetros padrão e certificados públicos sem custo | 2 parâmetros e 1 certificado |

O API Gateway e a VM t3.micro usam os créditos do plano gratuito, que cobrem com folga o período do trabalho. Para acompanhar: **Billing and Cost Management → Créditos**.

Para apagar tudo depois da entrega (no CloudShell):

```bash
aws cloudformation delete-stack --stack-name agenda-clinica
aws ssm delete-parameters --names /agenda-clinica/admin-password-hash /agenda-clinica/secret-key
```

Se tiver configurado o domínio, apague também o nome de domínio personalizado no API Gateway e o certificado no ACM.

## Rodar no seu computador (opcional)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                  # roda os 35 testes e mostra a cobertura
python main.py          # abre em http://127.0.0.1:5000 (os pedidos ficam só na memória)
```

Para entrar no painel localmente, defina antes `export ADMIN_PASSWORD_HASH="$(python3 scripts/gerar_hash_senha.py)"`.
