import os

import openai


def get_from_api(query: str, temperature=0, n=1):
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=temperature,
        n=n,
        messages=[
            {"role": "user", "content": "Q: " + query + "\nA:"}
        ],
    )
    # prompt="Q: "+query+"\nA:",
    # temperature=temperature,
    # max_tokens=128,
    # n=n,
    # frequency_penalty=0,
    # presence_penalty=0,
    # stop=["\n"]


class OpenAI:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
