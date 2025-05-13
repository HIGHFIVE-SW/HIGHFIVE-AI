from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity
import torch


tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')
domain_keywords = ["environment", "Society", "Economic", "technology"]

def get_embeddings(text: str):
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
    outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).detach().numpy()

def calculate_cosine_similarity(vec1, vec2):
    return cosine_similarity(vec1, vec2)

def extract_keywords(question: str):
    sentence_embedding = get_embeddings(question)
    domain_embeddings = [get_embeddings(keyword) for keyword in domain_keywords]
    similarities = [
        (keyword, calculate_cosine_similarity(sentence_embedding, embedding)[0][0])
        for keyword, embedding in zip(domain_keywords, domain_embeddings)
    ]
    return sorted(similarities, key=lambda x: x[1], reverse=True)