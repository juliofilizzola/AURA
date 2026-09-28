import uvicorn

from src.application import create_app


if __name__ == "__main__":
    uvicorn.run(
        create_app(), host="127.0.0.1", port=8000,
        access_log=False, proxy_headers=False, server_header=False,
        limit_concurrency=16,
    )
