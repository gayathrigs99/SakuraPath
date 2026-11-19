from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from src.routes.audio_routes import audio_router as audio_router
from src.routes.interview_routes import interview_router
from src.routes.report_routes import report_router
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn
from src.logger.logger import SakuraLogger
import os
from dotenv import load_dotenv

load_dotenv()

logger = SakuraLogger("main")

app = FastAPI(
    title="Sakura",
    description="AI oriented japanese interview practice",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL")],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(audio_router)
app.include_router(interview_router)
app.include_router(report_router)

@app.get("/health")
def check_health():
    """Return a simple liveness response to confirm the API process is running."""
    return {"status": "OK", "detail": "Health check successful"}


@app.get("/")
def serve_recorder():
    """Serve the backend's standalone audio-recorder page for manual testing."""
    return FileResponse("static/recorder.html")

if __name__ == "__main__":
    logger.info_log("App running on server")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
