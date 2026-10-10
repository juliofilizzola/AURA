# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Aura local — imagem de produção
# ---------------------------------------------------------------------------
# Usa build em dois estágios:
#   builder  — instala dependências em ambiente isolado
#   runtime  — imagem mínima sem ferramentas de build
# ---------------------------------------------------------------------------

FROM python:3.11-slim AS builder

WORKDIR /build

# Copia apenas o manifesto de dependências para aproveitar o cache do Docker
# enquanto o código-fonte não muda.
COPY pyproject.toml .

# Instala as dependências no diretório /deps para copiar no estágio final.
# --no-build-isolation é seguro aqui: setuptools já está presente na imagem.
RUN pip install --no-cache-dir --prefix=/deps -e . 2>/dev/null || \
    pip install --no-cache-dir --prefix=/deps \
        fastapi==0.141.1 \
        httpx==0.28.1 \
        pydantic==2.13.5 \
        python-dotenv==1.1.1 \
        uvicorn==0.54.0

# ---------------------------------------------------------------------------

FROM python:3.11-slim AS runtime

# Usuário sem privilégios — boa prática para containers de aplicação.
RUN useradd --no-create-home --shell /bin/false aura

WORKDIR /app

# Copia as dependências instaladas no estágio builder.
COPY --from=builder /deps /usr/local

# Copia o código-fonte da aplicação.
COPY main.py .
COPY src/ src/

# Garante que o usuário "aura" é dono dos arquivos.
RUN chown -R aura:aura /app

USER aura

# A Aura escuta na porta 8000 dentro do container.
# O docker-compose.yml publica essa porta apenas no loopback do host (127.0.0.1).
EXPOSE 8000

# Variáveis obrigatórias — devem ser fornecidas via docker-compose ou --env-file.
# Sem AURA_API_TOKEN a aplicação recusa inicializar.
ENV AURA_MODEL=llama3

CMD ["python", "main.py"]
