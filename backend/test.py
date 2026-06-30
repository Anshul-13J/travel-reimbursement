from llm.models import structured_llm

prompt = """
Return:

{
    "vendor":"test",
    "category":"Meals",
    "amount":100,
    "date":"01-01-2025",
    "confidence":0.95,
    "findings":[],
    "explanation":"test"
}
"""

print("Calling...")

result = structured_llm.invoke(
    prompt
)

print("DONE")

print(result)
print(type(result))

print(result.model_dump())