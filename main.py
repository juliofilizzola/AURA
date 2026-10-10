import os

import uvicorn

from src.application import create_app


if __name__ == "__main__":
    # Padrão seguro para execução local: loopback apenas.
    # Em container, defina AURA_HOST=0.0.0.0 via docker-compose (a porta é
    # publicada apenas no loopback do host pelo próprio compose).
    host = os.environ.get("AURA_HOST", "127.0.0.1")
    port = int(os.environ.get("AURA_PORT", "8000"))
    uvicorn.run(
        create_app(), host=host, port=port,
        access_log=False, proxy_headers=False, server_header=False,
        limit_concurrency=16,
    )

