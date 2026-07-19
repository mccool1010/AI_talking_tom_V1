from llama_cpp import Llama

llm = Llama(model_path="C:/tom/AI-Talking-Tom/backend/app/models/llm/tinyllama-1.1b-chat-v1.0.Q4_K_M (1).gguf",
            n_ctx=2048, n_threads=4)

prompt = "<|system|>\nYou are a friendly talking cat named Tom.</s>\n<|user|>\nHello, how are you?</s>\n<|assistant|>\n"

output = llm(prompt, max_tokens=256, stop=["</s>"], echo=False)
print(output["choices"][0]["text"])
