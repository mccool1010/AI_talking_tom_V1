from llm_service import LLMService

llm = LLMService()

while True:
    text = input("You: ")
    response = llm.generate(text,"sad")
    print("Tom:", response)