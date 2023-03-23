import base64
import os

from app import openapi_client
from app.openapi_client.api.collection_v1_api import COLLECTIONV1Api
from app.openapi_client.api.node_v1_api import NODEV1Api
from app.openapi_client.api_client import ApiClient
from app.openapi_client.configuration import Configuration


class EduSharingApiHelper:
    START_ID = '5e40e372-735c-4b17-bbf7-e827a5702b57'
    edu_sharing_api: ApiClient
    edu_sharing_collection_api: COLLECTIONV1Api
    edu_sharing_node_api: NODEV1Api
    def __init__(self):
        passwd = os.getenv("EDU_SHARING_PASSWORD")
        configuration = Configuration.get_default_copy()
        configuration.host = 'https://repository.staging.openeduhub.net/edu-sharing/rest'
        # doesn't work!
        configuration.username = 'admin'
        configuration.password = passwd
        self.edu_sharing_api = openapi_client.ApiClient(
            configuration=configuration,
            header_name='Authorization',
            header_value='Basic %s' % base64.b64encode(('admin:' + passwd).encode()).decode(),
        )

        self.edu_sharing_collection_api = openapi_client.COLLECTIONV1Api(self.edu_sharing_api)
        self.edu_sharing_node_api = openapi_client.NODEV1Api(self.edu_sharing_api)

    def run_over_collection_tree(self, execute_callback):
        self.run_over_collection_tree_internal(self.START_ID, execute_callback)

    def run_over_collection_tree_internal(self, collection_id, execute_callback, parent = []):
        collections = self.edu_sharing_collection_api.get_collections_subcollections(
            repository='-home-',
            collection=collection_id,
            scope='TYPE_EDITORIAL',
            max_items=100000,
            fetch_counts=False
        )
        for collection in collections.collections:
            execute_callback({'collection': collection, 'path': parent})
            parent_copy = parent.copy()
            parent_copy.append(collection)
            self.run_over_collection_tree_internal(collection.ref.id, execute_callback, parent_copy)
