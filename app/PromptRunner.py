import json
import logging
import threading
from io import StringIO

from app.EduSharingApiHelper import EduSharingApiHelper
from app.edu_sharing_api.models.node import Node
from app.RunMode import RunMode
from app.z_api.api.ai_text_prompts_api import AITextPromptsApi
import csv


class PromptRunner (threading.Thread):
    edu_sharing_api: EduSharingApiHelper
    z_api_text: AITextPromptsApi
    prompt: str
    mode: RunMode
    accumulator = []

    def __init__(self, z_api_text: AITextPromptsApi, prompt: str, mode: RunMode, node: Node):
        self.z_api_text = z_api_text
        self.prompt = prompt
        self.mode = mode
        self.node = node
        self.edu_sharing_api = EduSharingApiHelper()
        threading.Thread.__init__(self)

    def run(self):
        if self.mode == RunMode.COLLECTIONS:
            self.edu_sharing_api.run_over_collection_tree(lambda x: self.store_info(
                x
            )
         )
        self.write_csv()

    def store_info(self, data):
        node: Node
        converted_prompt: str
        if 'collection' in data:
            converted_prompt = self.prompt % {
                'title': data['collection'].properties['cm:title'],
                'description': data['collection'].properties['cm:description'],
                'path': data['path']
            }
            node = data['collection']
        try:
            api_result = self.z_api_text.prompt(body = converted_prompt)
            self.accumulator.append({
                # dirty hack!
                node: json.dumps(vars(node)),
                api_result: api_result,
                converted_prompt: converted_prompt,
            })
            self.write_csv()
        except Exception as e:
            self.accumulator.append({
                node: json.dumps(vars(node)),
                api_result: "API Error:" + str(e),
                converted_prompt: converted_prompt,
            })
            logging.warning(e)

    def write_csv(self):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerows(['ID', 'Titel', 'KI-Antwort', 'Gesendeter Prompt'])
        writer.writerows(map(lambda x: self.to_csv_line(x), self.accumulator))
        csv_data = output.getvalue()
        output.close()
        self.edu_sharing_api.edu_sharing_node_api.change_content_as_text(self.node.ref.repo, self.node.ref.id, 'text/csv', version_comment = 'Python OpenAI Wrapper', body = csv_data)

    def to_csv_line(self, x):
        node = json.loads(x.node)
        return [node.ref.id, node.title, x.api_result, x.converted_prompt]
