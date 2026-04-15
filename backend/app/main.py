from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import documents, chat, integrations, watcher

app = FastAPI(title="RAG Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(integrations.router)
app.include_router(watcher.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
