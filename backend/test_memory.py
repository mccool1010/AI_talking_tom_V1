# backend/test_memory.py

from llm_service import LLMService

llm = LLMService()

print("\nCurrent History:\n")
print(llm.history)

print("\nHistory Length:", len(llm.history))