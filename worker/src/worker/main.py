from fastapi import FastAPI

app = FastAPI(title="AI Review Content Factory — Worker")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
