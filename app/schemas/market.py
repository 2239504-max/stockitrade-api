from typing import Optional
from pydantic import BaseModel


class QuoteResponse(BaseModel):
    symbol: str
    market: str
    price: float
    currency: Optional[str] = None
    source: str = "kis"
