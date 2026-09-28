# Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes simulam Ollama e verificam contrato, autenticação, limites, sanitização,
isolamento de chamadas e concorrência. Faça também um teste manual sem internet com
o modelo instalado. As dependências diretas estão fixadas em `pyproject.toml`; atualize
com revisão e testes. Isso não substitui auditoria de vulnerabilidades nem fixa as
dependências transitivas.
