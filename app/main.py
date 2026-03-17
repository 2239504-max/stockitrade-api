from fastapi import FastAPI
from app.routers import domestic_stocks, overseas_stocks, domestic_derivatives, overseas_derivatives
from app.routers import portfolio

app = FastAPI(
    title="StockiTrade API",
    description="Portfolio tracking and market data API powered by KIS",
    version="0.1.0",
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "kis-fastapi"}

app.include_router(domestic_stocks.router)
app.include_router(overseas_stocks.router)
app.include_router(domestic_derivatives.router)
app.include_router(overseas_derivatives.router)
app.include_router(portfolio.router)
