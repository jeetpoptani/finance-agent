from fastapi import FastAPI

from app.routes.invoice import router

app = FastAPI(title="Autonomous Finance Agent", version="1.1.0")

app.include_router(router)


@app.get("/health")
def health():
	return {"status": "ok"}


@app.get("/ready")
def ready():
	return {"ready": True}
