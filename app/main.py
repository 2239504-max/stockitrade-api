from fastapi import FastAPI
from app.core.config import settings
from app.routers import domestic_stocks, overseas_stocks, domestic_derivatives, overseas_derivative
from app.routers import portfolio, market
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="StockiTrade API",
    description="Portfolio tracking and market data API powered by KIS",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
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
