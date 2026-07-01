from pydantic import BaseModel
from typing import List


class Finding(BaseModel):
    type: str
    description: str


class ReceiptSchema(BaseModel):
    vendor: str
    category: str
    amount: float
    date: str
    confidence: float
    findings: List[Finding] = []
    explanation: str = ""
