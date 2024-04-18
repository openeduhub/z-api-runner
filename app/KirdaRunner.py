import asyncio
import json
import logging
import os
import threading
from io import StringIO

import requests
from requests.auth import HTTPBasicAuth

from app.EduSharingApiHelper import EduSharingApiHelper
from app.edu_sharing_api.models.create_suggestion_request_dto import CreateSuggestionRequestDTO
from app.edu_sharing_api.models.node import Node
from app.RunMode import RunMode
from app.z_api import KidraApi, BayesianPredictionsPredictionData, BayesianPredictionsPredictionResult
from app.z_api.api.ai_text_prompts_api import AITextPromptsApi
import csv


class KidraRunner(threading.Thread):
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
            node_id = data['collection'].ref.id
            text = data['collection'].title
        else:
            node_id = data['node'].ref.id
            text = data['node'].title
        text = "a² + b² = c²"
        try:
            self.edu_sharing_api.edu_sharing_suggestion_api.create_suggestions(
                repository='-home-',
                node=node_id,
                type='AI',
                version = 'todo',
                create_suggestion_request_dto=[CreateSuggestionRequestDTO(
                    property_id="cclom:title",
                    value="test",
                    confidence=1,
                )]
            )
            #body = {"text": text, "reading_speed": 200, "generate_embeddings": False}
            #result = self.z_api_kidra.text_stats_analyze_text_post(body)
            api_result: BayesianPredictionsPredictionResult = self.z_api_kidra.predict_predict_post(
                bayesian_predictions_prediction_data=BayesianPredictionsPredictionData(
                    text=text,
                    num_samples=500,
                    num_predictions=10,
                    interval_site=0.8,
                )
            )
            predictions = api_result.predictions
            suggestions = []
            for k, v in predictions.items():
                suggestions.append(CreateSuggestionRequestDTO(
                    property_id=k.split('.')[1],
                    value=v["id"],
                    confidence=v["median_prob"],
                ))
                print(suggestions)
        except Exception as e:
            logging.warning(e)
