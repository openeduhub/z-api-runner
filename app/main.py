from typing import Union, List

from fastapi.params import Query
from pydantic import Field
import uvicorn
from fastapi import FastAPI
import os
import openai

app = FastAPI(
    title = "ChatGPT/OpenAI API Wrapper",
    version="0.0.1",
)

@app.get("/")
async def query(
        query: str = Query(
            description="Question to send to OpenAI"
        ),
        results: int = Query(
            default=1,
            description="Number of answers to resolve"
        )

) -> List[dict]:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    result = openai.Completion.create(
        model="text-davinci-003",
        prompt="Q: "+query+"\nA:",
        temperature=0.5,
        max_tokens=128,
        n=results,
        frequency_penalty=0,
        presence_penalty=0,
        stop=["\n"]
    )
    return result.choices

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)