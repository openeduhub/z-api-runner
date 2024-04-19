import asyncio
import json
import logging
import os
import threading

import requests

from app.EduSharingApiHelper import EduSharingApiHelper
from app.RunMode import RunMode
from app.edu_sharing_api.models.create_suggestion_request_dto import CreateSuggestionRequestDTO
from app.z_api import KidraApi


class KidraRunner(threading.Thread):
    minConfidence = 0.7
    is_stopped: bool
    edu_sharing_api: EduSharingApiHelper
    z_api_kidra: KidraApi
    mode: RunMode
    startId: str
    accumulator: list

    def stop(self):
        self.is_stopped = True

    def __init__(self, z_api_kidra: KidraApi, mode: RunMode, startId: str):
        self.is_stopped = False
        self.z_api_kidra = z_api_kidra
        self.mode = mode
        self.startId = startId
        self.accumulator = []
        self.edu_sharing_api = EduSharingApiHelper()
        threading.Thread.__init__(self)
        self.name = "KidraRunner"

    def run(self):
        if self.mode == RunMode.COLLECTIONS:
            asyncio.run(
                self.edu_sharing_api.run_over_collection_tree(self.startId, lambda x: self.create_suggestions(
                    x
                )
                                                              )
            )
        if self.mode == RunMode.MATERIALS:
            asyncio.run(
                self.edu_sharing_api.run_over_materials(lambda x: self.create_suggestions(
                    x
                )
                                                        )
            )

    async def create_suggestions(self, data):
        if self.is_stopped:
            return
        node_id: str
        text: str
        if 'collection' in data:
            node_id = data["collection"]["ref"]["id"]
            text = data["collection"]["title"]
        else:
            node_id = data["node"]["ref"]["id"]
            text = data["node"]["title"] + (data["node"]["cclom:general_description"].join('') if "cclom:general_description" in data["node"] else "")

        try:
            #body = {"text": text, "reading_speed": 200, "generate_embeddings": False}
            #result = self.z_api_kidra.text_stats_analyze_text_post(body)
            #api_result: BayesianPredictionsPredictionResult = self.z_api_kidra.predict_predict_post(
            #    bayesian_predictions_prediction_data=BayesianPredictionsPredictionData(
            ##        text=text,
            #        num_samples=500,
            #        num_predictions=10,
            #        interval_site=0.8,
            #    )
            #)
            url = os.getenv('Z_API_URL') + '/kidra/bayesian-predictions'
            headers = {
                'accept': 'application/json',
                'ai-prompt-token': os.getenv('Z_API_KEY'),
                'Content-Type': 'application/json'
            }
            data = {
                'text': text,
                'num_samples': 2000,
                'num_predictions': 10,
                'interval_size': 0.8
            }
            response = requests.post(url, headers=headers, json=data).json()

            predictions = response["predictions"]
            suggestions = []
            for k, v in predictions.items():
                for s in v:
                    if s["median_prob"] > self.minConfidence:
                        suggestions.append({
                            'propertyId': k.split('.')[1],
                            'value': s["id"],
                            'confidence': s["median_prob"],
                        })
            #
            #self.edu_sharing_api.edu_sharing_suggestion_api.create_suggestions(
            #    repository='-home-',
            #    node=node_id,
            #    type='AI',
            #    version = 'todo',
            #    create_suggestion_request_dto=[CreateSuggestionRequestDTO(
            #        property_id="cclom:title",
            #        value="test",
            #        confidence=1,
            #    )]
            #)
            url = self.edu_sharing_api.url + '/suggestions/v1/-home-/' + node_id + "?version=" + response["version"]
            headers = {
                'accept': 'application/json',
                'Authorization': "Basic %s" % self.edu_sharing_api.auth,
                'Content-Type': 'application/json'
            }
            response_delete = requests.delete(url, headers=headers)
            logging.info(response_delete.status_code)
            logging.info(json.dumps(suggestions))
            if len(suggestions):
                url = self.edu_sharing_api.url + '/suggestions/v1/-home-/' + node_id + "?version=" + response["version"]
                headers = {
                    'accept': 'application/json',
                    'Authorization': "Basic %s" % self.edu_sharing_api.auth,
                    'Content-Type': 'application/json'
                }
                response = requests.post(url, headers=headers, json=suggestions)
                logging.info(response.status_code != 200)
                if response.status_code != 200:
                    logging.warning(response.text)

            logging.info(text)
            logging.info(node_id)

        except Exception as e:
            logging.error(e)
