import os

import openai

class OpenAI:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
    def getFromAPI(self, query: str, temperature = 0, n = 1):
        return openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Q: "+query+"\nA:"}
            ],
        )
        # prompt="Q: "+query+"\nA:",
        # temperature=temperature,
        # max_tokens=128,
        # n=n,
        # frequency_penalty=0,
        # presence_penalty=0,
        # stop=["\n"]