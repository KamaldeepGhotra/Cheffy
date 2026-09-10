from fastapi import FastAPI

app = FastAPI(title="Cheffy API")


@app.get("/health")
def health_check():
    return {"status": "ok"}
