from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mira Lenormand API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hazelchen2000.github.io/mira-lenormand/"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

@app.get("/health")
def health():
    return {"status": "ok"}
