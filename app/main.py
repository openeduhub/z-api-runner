from typing import List

import uvicorn
import logging
from fastapi import FastAPI
from fastapi.params import Query
from fastapi.responses import PlainTextResponse

from app.EduSharingApiHelper import EduSharingApiHelper
from app.OpenAi import OpenAi

logging.root.setLevel(logging.INFO)
logging.info("Startup")

app = FastAPI(
    title="ChatGPT/OpenAI API Wrapper",
    version="0.0.1",
)

open_ai = OpenAi()
edu_sharing_api = EduSharingApiHelper()


def fill_description(x, prompt: str, property: str):
    if property in x['collection'].properties:
        if len(list(filter(None, x['collection'].properties[property]))) > 0:
            logging.info('Skip: ' + x['collection'].title)
            return
    path = ' - '.join(list(map(lambda x: x.title, x['path'])))
    title = x['collection'].title
    if path:
        title = path + ' - ' + title

    prompt = prompt % {
        'title': title
    }
    try:
        logging.info('Process: ' + x['collection'].title)
        description = open_ai.get_from_api(query=prompt)['choices'][0]['message']['content']
        if description:
            properties = x['collection'].properties
            keywords = []
            if 'cclom:general_keyword' in properties:
                keywords = properties['cclom:general_keyword']
                # filter empty strings
                keywords = list(filter(None, keywords))
            keywords.append("ChatGPT: Beschreibung")
            edu_sharing_api.edu_sharing_node_api.set_property(
                repository='-home-',
                node=x['collection'].ref.id,
                _property='cclom:general_keyword',
                value=keywords,
                keep_modified_date=True
            )
            edu_sharing_api.edu_sharing_node_api.set_property(
                repository='-home-',
                node=x['collection'].ref.id,
                _property=property,
                value=[description.strip()],
                keep_modified_date=True
            )

    except Exception as e:
        logging.warning(e)


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
    return open_ai.get_from_api(
        query=query,
        temperature=0.5,
        n=results
    ).choices


@app.get("/oeh-topics/description",
         response_class=PlainTextResponse,
         description="Get a csv response with all topics and generated descriptions"
         )
async def oeh_topics_description(
        prompt: str = Query(
            description="Prompt which is sent to OpenAI"
        ),
) -> str:
    edu_sharing_api.run_over_collection_tree(
        lambda x: fill_description(
            x,
           'Beschreibe folgendes Lehrplanthema spannend in 3 Sätzen: %(title)s',
           'cm:description')
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
