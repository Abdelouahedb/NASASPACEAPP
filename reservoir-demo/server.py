from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

@app.get("/api/comparison")
def comparison():
    return {
        "site": "Oued El Makhazine",
        "dates": ["2026-06-20", "2026-08-31"],
        "layers": ["/june.png", "/august.png", "/change.png"],
        "estimated_loss_km2_range": [1.9, 2.6],
    }

app.mount("/", StaticFiles(directory=Path(__file__).parent, html=True))
