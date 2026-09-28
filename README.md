# Aura local

API de chat em Python/FastAPI com inferência no Ollama da própria máquina.
Não usa provedor externo, não baixa modelos automaticamente e não salva conversas.
Requer Python 3.11+ e Ollama com um modelo local instalado. O consumo de RAM/VRAM
depende do modelo; o padrão preservado do projeto é `llama3`.

## Preparação no Windows / PowerShell

Instale o Ollama pela distribuição oficial. Antes de iniciar o **processo do Ollama**,
configure estas variáveis no terminal que irá executá-lo:

```powershell
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NO_CLOUD = '1'
ollama serve
```

Se o aplicativo Ollama já estiver na bandeja, encerre-o antes de executar esse comando.
As variáveis precisam chegar ao processo do motor; defini-las apenas na Aura não altera
um Ollama já em execução. Use uma versão atual que suporte `OLLAMA_NO_CLOUD`.

Em outro terminal, baixe uma vez o modelo (essa etapa precisa de internet):

```powershell
ollama pull llama3
```

Para preparar as dependências da Aura, na raiz do projeto:

```powershell
python -m venv .venv  # somente se ainda não existir
.\.venv\Scripts\python.exe -m pip install -e .
```

Instalação de pacotes/modelos usa a rede; após a preparação, a inferência pode funcionar
sem internet. Para isolamento forte, bloqueie a saída de rede do Ollama no firewall ou
desconecte a máquina e teste o modelo. Não use modelos remotos/cloud nem aliases deles.

## Executar

No terminal da Aura, gere um token aleatório por sessão e inicie:

```powershell
$env:AURA_API_TOKEN = & .\.venv\Scripts\python.exe -c 'import secrets; print(secrets.token_urlsafe(32))'
$env:AURA_MODEL = 'llama3'
.\.venv\Scripts\python.exe main.py
```

A API escuta em `127.0.0.1:8000`; o Ollama fica em `127.0.0.1:11434`.
A ausência de um token válido impede a inicialização. O projeto não carrega `.env`
automaticamente. Não coloque tokens reais em código, commits ou exemplos HTTP.

O cliente deve herdar o mesmo `AURA_API_TOKEN`. Por exemplo, interrompa a API com
Ctrl+C e reinicie em um processo filho, preservando o ambiente e liberando o terminal:

```powershell
$auraProcess = Start-Process -FilePath '.\.venv\Scripts\python.exe' -ArgumentList 'main.py' -WindowStyle Hidden -PassThru
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/chat' -Method Post -ContentType 'application/json; charset=utf-8' -Headers @{ Authorization = "Bearer $env:AURA_API_TOKEN" } -Body ([System.Text.Encoding]::UTF8.GetBytes('{"msg":"Olá, explique o que é uma IA local."}'))
Stop-Process -Id $auraProcess.Id
```

Aguarde a inicialização antes de enviar a primeira requisição. O exemplo em
`test_main.http` também lê o token do ambiente do cliente HTTP (reinicie a IDE com
esse ambiente, se necessário). A resposta é `{"result":"..."}`. `model_name` é
opcional e, se enviado, precisa coincidir com `AURA_MODEL`.

`GET /api/health` exige o mesmo token e confirma apenas que a API está funcionando;
não confirma que Ollama/modelo estão prontos. A rota provisória `/generate` foi removida.

## Organização

| Arquivo | Responsabilidade |
| --- | --- |
| `main.py` | Inicialização local e limites do servidor |
| `src/application.py` | Composição, ciclo de vida do cliente HTTP e erros |
| `src/config.py` | Configuração validada por ambiente |
| `src/security.py` | Autenticação, origem, host e limite de corpo |
| `src/router.py` | Contrato HTTP e encaminhamento |
| `src/schema.py` | Validação de entrada e saída |
| `src/service.py` | Inferência assíncrona e limites do Ollama |
| `src/ollama_client.py` | Transporte limitado e verificação de modelo local |
| `src/erros.py` | Erros públicos sem detalhes internos |
| `tests/test_api.py` | Testes sem modelo, GPU ou rede |

## Segurança e privacidade

- O cliente do motor usa endereço loopback fixo, ignora proxies do ambiente e não
  segue redirecionamentos. Antes de enviar o prompt, consulta `/api/show` e exige
  metadados de pesos locais, recusando campos de modelo remoto e metadados ausentes.
  Não há fallback para nuvem. Motores incompatíveis falham de forma fechada.
- Token obrigatório, comparação em tempo constante, hosts locais e rejeição de
  requisições com `Origin`. Não há CORS nem interface web neste projeto.
- Corpo limitado a 64 KiB, mensagem a 8.000 caracteres, uma geração por vez,
  resposta a 256 KiB e geração a 512 tokens em contexto de 4.096 tokens.
  Corpo lento expira em 10 segundos e inferência em 120 segundos. Timeout do cliente
  não garante interrupção imediata do processamento dentro do motor.
- Sem histórico persistente ou logs de acesso. Validação e falhas conhecidas não
  devolvem prompts, tokens ou detalhes internos. Respostas usam `Cache-Control: no-store`.
- Sem ferramentas, execução de comandos, leitura de arquivos ou busca na internet
  disponíveis ao modelo. Trate a resposta como texto não confiável; não execute código
  sugerido automaticamente. Cada chamada é independente, sem memória de conversa.

O loopback não protege contra malware ou outros processos da mesma máquina. O Ollama
tem API própria sem o token da Aura: mantenha-o no loopback. A política de nuvem deve
ser desativada no próprio motor conforme acima. A checagem de metadados e o bloqueio
de nomes com `cloud` são proteções adicionais: a Aura precisa confiar no daemon local.
Dados passam pela RAM e podem aparecer em swap, dumps ou ferramentas de diagnóstico
do sistema/motor. Não existe garantia de apagamento seguro de memória em Python.
Não exponha portas via túnel, proxy ou `0.0.0.0`. Os limites pressupõem um único processo.

Erros: `401` token, `403` origem, `413` tamanho, `415` tipo de conteúdo, `422` validação,
`429` ocupação, `502` resposta/falha do motor, `503` indisponibilidade/modelo ausente,
`504` timeout. Verifique instalação e nome do modelo em caso de `503`.

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes simulam Ollama e verificam contrato, autenticação, limites, sanitização,
isolamento de chamadas e concorrência. Faça também um teste manual sem internet com
o modelo instalado. As dependências diretas estão fixadas em `pyproject.toml`; atualize
com revisão e testes. Isso não substitui auditoria de vulnerabilidades nem fixa as
dependências transitivas.
