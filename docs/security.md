# Segurança e privacidade

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
ser desativada no próprio motor conforme o guia de [instalação](getting-started.md). A checagem de metadados e o bloqueio
de nomes com `cloud` são proteções adicionais: a Aura precisa confiar no daemon local.
Dados passam pela RAM e podem aparecer em swap, dumps ou ferramentas de diagnóstico
do sistema/motor. Não existe garantia de apagamento seguro de memória em Python.
Não exponha portas via túnel, proxy ou `0.0.0.0`. Os limites pressupõem um único processo.

Erros: `401` token, `403` origem, `413` tamanho, `415` tipo de conteúdo, `422` validação,
`429` ocupação, `502` resposta/falha do motor, `503` indisponibilidade/modelo ausente,
`504` timeout. Verifique instalação e nome do modelo em caso de `503`.
