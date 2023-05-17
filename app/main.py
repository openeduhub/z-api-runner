import base64
import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.params import Query
from fastapi.responses import PlainTextResponse
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

import z_api
from app.EduSharingApiHelper import EduSharingApiHelper
from app.OpenAi import OpenAi
from app.valuespace_converter.app.valuespaces import Valuespaces

logging.root.setLevel(logging.INFO)
logging.info("Startup")

transport = AIOHTTPTransport(
    url=os.getenv("EDU_SHARING_URL") + '/graphql',
    headers={
        'Authorization': 'Basic ' + base64.b64encode(
            ('admin:' + os.getenv("EDU_SHARING_PASSWORD")).encode('utf-8')).decode('utf-8')
    }
)
valuespaces = Valuespaces()
graphqlClient = Client(transport=transport, fetch_schema_from_transport=True)
app = FastAPI(
    title="ChatGPT/OpenAI API Wrapper",
    version="0.0.1",
)
z_api_config = z_api.Configuration.get_default_copy()
z_api_config.api_key = {'ai-prompt-token': os.getenv("Z_API_KEY")}
z_api_client = z_api.ApiClient(configuration=z_api_config)
z_api_text = z_api.TextPromptControllerApi(z_api_client)
logging.info(z_api_text.prompt(query="Hallo Welt"))

open_ai = OpenAi()
edu_sharing_api = EduSharingApiHelper()


async def fill_discipline(x, prompt: str, property: str):
    p = x['node'].properties
    text = ' '.join(p['cclom:title'] if 'cclom:title' in p else '' + p[
        'cclom:general_description'] if 'cclom:general_description' in p else '').strip()
    logging.info(x['node'].ref.id)
    if text:
        prompt = prompt % {
            'text': text
        }
        logging.info('Prompt: ' + prompt)
        data = z_api_text.prompt(query=prompt).responses[0].strip()
        key = valuespaces.findKeyByLabel('discipline', data)
        logging.info(data)
        logging.info(key)
        if key:
            request = gql("""
            mutation addOrUpdateSuggestion($suggestion: SuggestionInput!) {
                addOrUpdateSuggestion(suggestion: $suggestion) 
            }
            """)
            await graphqlClient.execute_async(request, variable_values={
                "suggestion": {
                    "nodeId": x['node'].ref.id,
                    "id": "Z-API",
                    "type": "AI",
                    "lom": {
                        "classification": {
                            "taxon": {
                                "value": {
                                    "id": key['id'],
                                    "value": key['id']
                                },
                                "version": "1.0",
                                "info": {
                                    "status": "PENDING"
                                }
                            }
                        }
                    }
                }
            })


def fill_property(x, prompt: str, property: str):
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
        description = z_api_text.prompt(query=prompt)
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


@app.get("/materials/discipline",
         response_class=PlainTextResponse,
         description="Get a recommended discipline for given topics"
         )
async def oeh_materials(
) -> str:
    await edu_sharing_api.run_over_materials(
        lambda x: fill_discipline(
            x,
            'Für welches Schulfach bzw. Fachgebiet eignet sich folgender Inhalt: %(text)s (nur das Fach ausgeben)',
            'lom.classification.taxon')
    )
    return ''


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
        lambda x: fill_property(
            x,
            'Beschreibe folgendes Lehrplanthema spannend in 3 Sätzen: %(title)s',
            'cm:description')
    )
    return ''


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
