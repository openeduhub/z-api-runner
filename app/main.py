import csv
import io
from typing import Union, List

from fastapi.params import Query
from pydantic import Field
from fastapi.responses import PlainTextResponse

from app.OpenAi import OpenAI
from valuespace_converter.app.valuespaces import Valuespaces
import uvicorn
from fastapi import FastAPI
import os
import openai

app = FastAPI(
    title="ChatGPT/OpenAI API Wrapper",
    version="0.0.1",
)
valuespaces = Valuespaces()
openAI = OpenAI()


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
    return openAI.getFromAPI(
        query=query,
        temperature=0.5,
        n=results
    ).choices


@app.get("/oeh-topics/description",
         response_class=PlainTextResponse,
         description="Get a csv response with all topics and generated descriptions"
         )
async def oeh_topics_description(
        topic: str = Query(
            description="Name of the primary topic to resolve, e.g. Physik"
        ),
) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    return toCSV(resolveTree(valuespaces.data['oeh-topics'], [], topic))

def toCSV(data):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';',
                        quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['SKOS ID', 'Node ID', 'Caption', 'Description ChatGPT', 'Query Prompt'])
    for d in data:
        writer.writerow([
            d['skos']['id'],
            d['skos']['id'].split('/')[-1],
            d['skos']['prefLabel']['de'],
            d['description'],
            d['query']
        ])
    return output.getvalue()
def resolveTree(
        tree,
        parent=[],
        condition=None
):
    result = []
    for leave in tree:
        if condition and leave['prefLabel']['de'] != condition:
            continue
        query = "Beschreibe folgendes Lehrplanthema spannend in 3 Sätzen: \"" + leave['prefLabel']['de']

        if 'description' in leave and 'de' in leave['description']:
            query += " (" + leave['description']['de'] + ")"
        if len(parent):
            query += " (" + ' - '.join(map(lambda x: x['prefLabel']['de'], parent)) + ")"
        query += "\""

        try:
            result.append({
                "query": query,
                "description": openAI.getFromAPI(query)['choices'][0]['message']['content'],
                "skos": {
                    "id": leave['id'],
                    "prefLabel": leave['prefLabel']
                }
            })
            print(result)
        except Exception as e:
            print(e)
            # return result
        if 'narrower' in leave:
            sub_parent = parent.copy()
            sub_parent.append(leave)
            result.extend(resolveTree(leave['narrower'], sub_parent))

    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
