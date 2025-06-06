import os
from langchain_openai import OpenAIEmbeddings

from server.logger import logger

openai_dimension_size:int = 1536

weaviate_index_name = "Activities"

weaviate_headers={
    "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY"),
    "X-HuggingFace-Api-Key": os.getenv("HUGGINGFACE_API_KEY"),
    "X-Cohere-Api-Key": os.getenv("COHERE_APIKEY"),
}

from sentence_transformers import SentenceTransformer

logger.info("BAAI/bge-m3 모델 생성 중...")
model = SentenceTransformer("BAAI/bge-m3")
logger.info("BAAI/bge-m3 모델 생성 완료.")

def embed(text):
    return model.encode(text, normalize_embeddings=True)

