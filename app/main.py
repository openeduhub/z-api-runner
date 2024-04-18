import base64
import threading
from datetime import datetime
import asyncio
import logging
import os
from threading import Thread
from typing import List

import uvicorn
from fastapi import FastAPI
from fastapi.params import Query
from fastapi.responses import PlainTextResponse
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from starlette.responses import JSONResponse

import z_api
from app.EduSharingApiHelper import EduSharingApiHelper
from app.KirdaRunner import KidraRunner
from app.OpenAi import OpenAi
from app.PromptRunner import PromptRunner
from app.RunMode import RunMode
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
    title="OpenAI/Kidra API Wrapper",
    version="0.0.2",
)
z_api_config = z_api.Configuration.get_default_copy()
z_api_config.api_key = {'ai-prompt-token': os.getenv("Z_API_KEY")}
z_api_config.client_side_validation = False
z_api_client = z_api.ApiClient(configuration=z_api_config)
z_api_text = z_api.AITextPromptsApi(z_api_client)
z_api_kidra = z_api.KidraApi(z_api_client)
# logging.info(z_api_text.prompt(body="Hallo Welt"))

open_ai = OpenAi()
edu_sharing_api = EduSharingApiHelper()


# curl -X 'POST' \
#         'https://ai-prompt-service.staging.openeduhub.net/kidra/bayesian-predictions' \
#         -H 'accept: application/json' \
#               -H 'Content-Type: application/json' \
#                  -d '{
# "text": "a² + b² = c²",
# "num_samples": 1000,
# "num_predictions": 10,
# "interval_size": 0.8
# }'
# {
#     "predictions": {
#         "properties.ccm:curriculum": [
#             {
#                 "id": "http://w3id.org/openeduhub/vocabs/oeh-topics/858f8170-15a2-4c7a-8cbd-a0f94b02e6cd",
#                 "name": "Außerschulisches Lernen",
#                 "mean_prob": 0.35047292709350586,
#                 "median_prob": 0.3210128843784332,
#                 "prob_interval": [
#                     0.05755974352359772,
#                     0.5337174534797668
#                 ]
#             },

async def fill_discipline(x, prompt: str, property: str):
    p = x['node'].properties
    text = ' '.join(
        (p['cclom:title'] if 'cclom:title' in p else '') +
        (p['cclom:general_description'] if 'cclom:general_description' in p else '')
    ).strip()
    logging.info(x['node'].ref.id)
    if text:
        prompt = prompt % {
            'text': text
        }
        logging.info('Prompt: ' + prompt)
        try:
            data = z_api_text.prompt(body=prompt).responses[0].strip()
            key = valuespaces.findInText('discipline', data)
            logging.info(data)
            logging.info(key)
            if key:
                taxon = []
                for k in key:
                    taxon.append({
                        "value": {
                            "id": k['id'],
                            "value": k['prefLabel']['de']
                        },
                        "version": "1.0",
                        "info": {
                            "status": "PENDING"
                        }
                    })
                request = gql("""
                mutation addOrUpdateSuggestion($suggestion: SuggestionInput!) {
                    addOrUpdateSuggestion(suggestion: $suggestion) 
                }
                """)
                suggestion = {
                    "nodeId": x['node'].ref.id,
                    "id": "Z-API",
                    "type": "AI",
                    "lom": {
                        "classification": {
                            "taxon": taxon
                        }
                    },
                    "oeh": {}
                }
                logging.info(suggestion)
                await graphqlClient.execute_async(request, variable_values={
                    "suggestion": suggestion
                })
        except Exception as e:
            logging.warning('Z Api failed', e)


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
        description = z_api_text.prompt(body=prompt)
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

@app.delete("/run_prompt/stop",
         response_class=PlainTextResponse,
         description="""
         Laufenden Prompt abbrechen/beenden
         """
         )
async def stop_prompt(
        prompt_id: str
) -> None:
    thread = list((filter(lambda x: x.name == prompt_id, threading.enumerate())))[0]
    thread.stop()

@app.get("/run_prompt/running",
         response_class=PlainTextResponse,
         description="""
         Aktuell laufende Prompts prüfen
         """
         )
async def running_prompts(
) -> JSONResponse:
    return JSONResponse(content=list((map(lambda x: {
        'url': x.name,
        'progress': len(x.accumulator)
    }, filter(lambda x: x.name.startswith('https://'), threading.enumerate())))
                                     ))
@app.get("/run_prompt",
         response_class=PlainTextResponse,
         description="""Definierten Prompt über alle Materialien oder Sammlungen ausführen. 
         Folgende Platzhaler sind verwendbar:
         %(title)s => Titel des Mediums/Sammlung
         %(description)s => Beschreibung des Mediums/Sammlung
         %(path)s => Vollständiger Sammlungspfad inkl. der Sammlung selbst (nur Sammlungen)
         """
         )
async def run_prompt(
    prompt: str,
    mode: RunMode,
    start_Id: str = Query(default = None, description="Start Id (nur Sammlungen), wenn nicht gesetzt wird der gesamte Baum verwendet"),
) -> str:

    result = edu_sharing_api.edu_sharing_node_api.create_child("-home-", "-inbox-", "ccm:io", {
        "cm:name": [prompt + " " + datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + ".csv"]
    }).node

    run = PromptRunner(z_api_text, prompt, mode, start_Id, result)
    run.start()
    return run.name

@app.get("/run_kidra_suggestions",
         response_class=PlainTextResponse,
         description=""" Kidra über alle Nodes Vorschläge generieren lassen
         """
         )
async def run_kidra_suggestions(
        mode: RunMode,
        start_Id: str = Query(default = None, description="Start Id (nur Sammlungen), wenn nicht gesetzt wird der gesamte Baum verwendet"),
) -> str:
    run = KidraRunner(z_api_kidra, mode, start_Id)
    run.accumulator = []
    run.start()
    return run.name


@app.get("/materials/discipline",
         response_class=PlainTextResponse,
         description="Get a recommended discipline for given topics"
         )
async def oeh_materials(
) -> str:
    await edu_sharing_api.run_over_materials(
        lambda x: fill_discipline(
            x,
            'Für welche Schulfächer bzw. Fachgebiete eignet sich folgender Inhalt (Nur die Fächer benennen): %(text)s',
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
    uvicorn.run(app, host="0.0.0.0", port=8001)
