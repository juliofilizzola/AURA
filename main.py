from fastapi import FastAPI
from src.router import router
import uvicorn

app = FastAPI(title="Aura API", description="API for Aura text generation", version="1.0.0")

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=11434)
