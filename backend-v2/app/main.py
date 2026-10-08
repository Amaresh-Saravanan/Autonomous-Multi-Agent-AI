from fastapi import FastAPI

app = FastAPI(title="Disaster Response Platform v2")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
