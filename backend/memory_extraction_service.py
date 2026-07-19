from llama_cpp import Llama
import json

class MemoryExtractionService:

    def __init__(self):

        print("Loading Memory Extraction Service...")

        self.model = Llama(
            "C:/tom/AI-Talking-Tom/models/llm/qwen2.5-3b-instruct-q4_k_m.gguf",
            n_ctx=1024,
            verbose=False
        )

        print("Memory Extraction Ready")
    def extract(self, text):
        prompt = f"""
You are a memory extraction engine.

Extract ONLY personal information about the user.

Return ONLY valid JSON.

Rules:

likes:
- hobbies
- favorite things
- interests

dislikes:
- things the user dislikes

facts:
- personal facts
- projects
- goals
- experiences

DO NOT explain anything.

DO NOT summarize anything.

DO NOT invent facts.

DO NOT describe what something is.

Good example:
 User:
  My favorite OS is Linux Mint.

 Output:
  {{
  "likes":["Linux Mint"],
  "dislikes":[],
  "facts":[]
  }}

 User:
  I am building an AI Talking Tom project.

 Output:
 {{
  "likes":[],
  "dislikes":[],
  "facts":["Building AI Talking Tom project"]
 }}

 Now extract memory from: {text}
"""
        response = self.model.create_chat_completion(
    messages=[
        {
            "role": "system",
            "content": "You are a memory extraction engine. Return only JSON."
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    temperature=0,
    max_tokens=100
)
        result = response["choices"][0]["message"]["content"]
        print("MEMORY RAW:", result)
        try:
            start = result.find("{")
            end = result.rfind("}") + 1

            json_text = result[start:end]

            print("JSON TEXT:", json_text)

            data = json.loads(json_text)
            if not all( key in data for key in ["likes", "dislikes", "facts"]):
                 raise ValueError("Invalid schema")

            return data

        except Exception as e:
            print("JSON ERROR:", e)

            return {
        "likes": [],
        "dislikes": [],
        "facts": []
    }
        