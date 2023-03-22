import os

import openai

from app import openapi_client
from app.openapi_client.api.collection_v1_api import COLLECTIONV1Api
from app.openapi_client.api_client import ApiClient
from app.openapi_client.configuration import Configuration


class EduSharingCollectionRunner:#
    START_ID = '5e40e372-735c-4b17-bbf7-e827a5702b57'
    edu_sharing_api: ApiClient
    edu_sharing_collection_api: COLLECTIONV1Api
    def __init__(self):
        configuration = Configuration.get_default_copy()
        configuration.host = 'https://repository.staging.openeduhub.net/edu-sharing/rest'
        self.edu_sharing_api = openapi_client.ApiClient(configuration=configuration)
        self.edu_sharing_collection_api = openapi_client.COLLECTIONV1Api(self.edu_sharing_api)

    def run_over_collection_tree(self, execute_callback):
        self.run_over_collection_tree_internal(self.START_ID, execute_callback)

    def run_over_collection_tree_internal(self, collection_id, execute_callback):
        collections = self.edu_sharing_collection_api.get_collections_subcollections(
            repository='-home-',
            collection=collection_id,
            scope='TYPE_EDITORIAL',
            max_items=100000,
            fetch_counts=False
        )
        for collection in collections['collections']:
            print(collection)
