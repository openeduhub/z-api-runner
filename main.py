import uvicorn
from fastapi import FastAPI
import os
import openai

app = FastAPI()


@app.get("/")
async def query(query: str):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    result = openai.Completion.create(
      model="text-davinci-003",
      prompt="Q: "+query+"\nA:",
      temperature=0.5,
      max_tokens=128,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0,
      stop=["\n"]
    )
    return result.choices[0]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)