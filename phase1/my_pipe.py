import subprocess
import sys
import os
import logging
import torch
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModel
from ollama import Client

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_and_install_packages():
    required_packages = [
        "torch", 
        "pydantic", 
        "elasticsearch", 
        "python-dotenv", 
        "transformers", 
        "ollama"
    ]
    installed_packages = subprocess.run(['pip', 'list'], capture_output=True, text=True).stdout

    for package in required_packages:
        if package not in installed_packages:
            print(f"Installing {package}...")
            install_package(package)
        else:
            print(f"{package} is already installed")

# Ensure necessary packages are installed at the start
check_and_install_packages()

class Pipeline:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.name = "RAG Pipeline"
        self.valves = self.Valves()
        self._load_env()
        self.es = self._init_es_client()
        self.client = Client()
        self.tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
        self.model = AutoModel.from_pretrained('bert-base-uncased')

    def _load_env(self):
        dotenv_path = ".env"
        load_dotenv(dotenv_path=dotenv_path)

    def _init_es_client(self) -> Elasticsearch:
        es_host = os.getenv("ELASTICSEARCH_HOST")
        es_user = os.getenv("ELASTICSEARCH_USER")
        es_pass = os.getenv("ELASTICSEARCH_PASS")
        return Elasticsearch(hosts=[es_host], basic_auth=(es_user, es_pass))

    async def on_startup(self):
        logging.info("Pipeline starting up")

    async def on_shutdown(self):
        logging.info("Pipeline shutting down")

    def knn_search(self, index, field, query_vector, k=10) -> List[dict]:
        search_body = {
            "knn": {
                "field": field,
                "query_vector": query_vector.tolist(),  # Ensure the vector is in list format
                "k": k,
                "num_candidates": 100
            },
            "_source": ["description", "solution", "combined_text", "cicore_id_name", "is_alert", "stage_id_name", "handle_type", "team_category", "owner_id_name"]
        }
        try:
            response = self.es.search(index=index, body=search_body)
            return response['hits']['hits']
        except Exception as e:
            logging.error(f"Elasticsearch search error: {e}")
            return []

    def generate_query_vector(self, query) -> torch.Tensor:
        inputs = self.tokenizer(query, return_tensors='pt', padding=True, truncation=True)
        with torch.no_grad():
            output = self.model(**inputs).last_hidden_state.mean(dim=1).squeeze(0)
        return output

    def generate_text_with_context(self, context, query) -> Union[str, Generator, Iterator]:
        stream = self.client.chat(
            model='llama3',
            messages = [
            {'role': 'user', 'content': f"{context}\n\nQuery: {query}"}
        ],
            stream=True,
        )
        for chunk in stream:
            yield chunk

    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Generator, Iterator]:
        logging.info("Processing pipeline")

        index_name = 'ticket_similarity'
        field_name = 'combined_text_vector'

        query_vector = self.generate_query_vector(user_message)
        results = self.knn_search(index=index_name, field=field_name, query_vector=query_vector, k=10)
        retrieved_docs = [hit['_source'] for hit in results]

        context = " ".join([doc['combined_text'] for doc in retrieved_docs])
        response = self.generate_text_with_context(context, user_message)

        return response if response else "No Information Found"
