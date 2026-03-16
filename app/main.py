from fastapi import FastAPI
from app.routers import domestic_stocks, overseas_stocks, domestic_derivatives, overseas_derivatives

app = FastAPI(title="KIS Multi-Asset API")

@app.get("/health")
def health():
    return {"status": "ok", "service": "kis-fastapi"}

app.include_router(domestic_stocks.router)
app.include_router(overseas_stocks.router)
app.include_router(domestic_derivatives.router)
app.include_router(overseas_derivatives.router)
