from pydantic import BaseModel
from typing import List, Optional


class Finding(BaseModel):

    type: str
    description: str
    amount: Optional[float] = None


class ReceiptSchema(BaseModel):

    vendor: str
    category: str
    amount: float
    date: str
    confidence: float
    findings: List[Finding]
    explanation: str