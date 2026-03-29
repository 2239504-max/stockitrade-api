from fastapi import FastAPI
from app.core.config import settings
from app.routers import domestic_stocks, overseas_stocks, domestic_derivatives, overseas_derivatives
from app.routers import portfolio, market, events
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="StockiTrade API",
    description="Portfolio tracking and market data API powered by KIS",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://stockitrade.com",
        "https://stockitrade.com",
        "http://www.stockitrade.com",
        "https://www.stockitrade.com",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "kis-fastapi"}

app.include_router(domestic_stocks.router)
app.include_router(overseas_stocks.router)
app.include_router(domestic_derivatives.router)
app.include_router(overseas_derivatives.router)
app.include_router(portfolio.router)
app.include_router(events.router)
