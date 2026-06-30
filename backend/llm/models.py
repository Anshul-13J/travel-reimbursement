from langchain_ollama import ChatOllama
from llm.schema import ReceiptSchema


local_llm = ChatOllama(
    model="gemma3:4b",
    temperature=0
)

structured_llm = (
    local_llm
    .with_structured_output(
        ReceiptSchema
    )
)