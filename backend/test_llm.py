from llm_service import LLMService

print("Creating LLM Service...")

llm = LLMService()

print("Generating response...")

response = llm.generate("Hello Tom")

print(response)