import asyncio
import json
import logging
import os
import threading
from io import StringIO

import requests
from requests.auth import HTTPBasicAuth

from app.EduSharingApiHelper import EduSharingApiHelper
from app.edu_sharing_api.models.node import Node
from app.RunMode import RunMode
from app.z_api.api.ai_text_prompts_api import AITextPromptsApi
import csv


class PromptRunner (threading.Thread):
    is_stopped: bool
    edu_sharing_api: EduSharingApiHelper
    z_api_text: AITextPromptsApi
    prompt: str
    mode: RunMode
    accumulator: list

    def getName(self) -> str:
        return self.prompt

    def stop(self):
        self.is_stopped = True
    def __init__(self, z_api_text: AITextPromptsApi, prompt: str, mode: RunMode, node: Node):
        self.is_stopped = False
        self.z_api_text = z_api_text
        self.prompt = prompt
        self.mode = mode
        self.node = node
        self.accumulator = []
        self.edu_sharing_api = EduSharingApiHelper()
        threading.Thread.__init__(self)

    def run(self):
        if self.mode == RunMode.COLLECTIONS:
            asyncio.run(
                self.edu_sharing_api.run_over_collection_tree(lambda x: self.store_info(
                    x
                )
                                                              )
            )
        if self.mode == RunMode.MATERIALS:
            asyncio.run(
                self.edu_sharing_api.run_over_materials(lambda x: self.store_info(
                    x
                )
                                                        )
            )
        self.write_csv()

    async def store_info(self, data):
        if self.is_stopped:
            return
        node: Node
        converted_prompt: str
        if 'collection' in data:
            path = ' - '.join(list(map(lambda x: x.title, data['path'])))
            title = data['collection'].title
            if path:
                path = path + ' - ' + title
            else:
                path = title
            converted_prompt = self.prompt % {
                'title': data['collection'].title,
                'description': data['collection'].properties['cm:description'],
                'path': path
            }
            node = data['collection']
        else:
            props = data['node'].properties
            converted_prompt = self.prompt % {
                'title': data['node'].title,
                'description': props['cclom:general_description'] if 'cclom:general_description' in props else '',
            }
            node = data['node']
        try:
            api_result = self.z_api_text.prompt(body = converted_prompt)
            result = api_result.responses[0].encode('utf-8').decode('unicode_escape')
            self.accumulator.append(self.to_csv_line(node,
                                                     # seems to be a dirty hack because of the openapi generator
                                                     result,
                                                     converted_prompt,
                                                     ))
            logging.info(node.ref.id + ": " + result)
            logging.info(len(self.accumulator))
            if len(self.accumulator) % 50 == 1:
                self.write_csv()
        except Exception as e:
            self.accumulator.append(self.to_csv_line(node,
                                                     "API Error:" + str(e),
                                                     converted_prompt,
                                                     ))
            logging.warning(e)

    def write_csv(self):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Titel', 'KI-Antwort', 'Gesendeter Prompt'])
        writer.writerows(self.accumulator)
        csv_data = output.getvalue()
        result = requests.post(os.getenv('EDU_SHARING_URL') + '/rest/node/v1/nodes/' + self.node.ref.repo + '/' + self.node.ref.id + '/content?mimetype=text/csv', files={
            'file': ('dummy.csv', csv_data)
        }, auth=HTTPBasicAuth('admin', os.getenv('EDU_SHARING_PASSWORD'))).json()
        output.close()
        # self.edu_sharing_api.edu_sharing_node_api.change_content1(self.node.ref.repo, self.node.ref.id, 'text/csv',
        #                                                          version_comment = 'Python OpenAI Wrapper',
        #                                                          post_params = {'file': csv_data}
        #                                                          )

    def to_csv_line(self, node, api_result, converted_prompt):
        return [node.ref.id, node.title,api_result, converted_prompt]
