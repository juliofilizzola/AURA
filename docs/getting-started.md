# Instalação e execução

Execute os comandos na raiz do projeto.

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
`examples/chat.http` também lê o token do ambiente do cliente HTTP (reinicie a IDE com
esse ambiente, se necessário). A resposta é `{"result":"..."}`. `model_name` é
opcional e, se enviado, precisa coincidir com `AURA_MODEL`.

`GET /api/health` exige o mesmo token e confirma apenas que a API está funcionando;
não confirma que Ollama/modelo estão prontos. A rota provisória `/generate` foi removida.
