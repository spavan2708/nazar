from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=[],
)


@app.get("/")
def read_root():
    return {"message": "Nazar API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
