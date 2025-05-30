from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')
domain_keywords = ["Economy", "Environment", "Technology", "People", "Society"]

def get_embeddings(text: str):
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
    outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).detach().numpy()

def calculate_cosine_similarity(vec1, vec2):
    return cosine_similarity(vec1, vec2)

def extract_keywords(question: str):
    """
    텍스트로부터 키워드를 추출하는 함수

    Args:
        question (str): 키워드를 추출하고자 하는 문자열
    Returns:
        str: 가장 유사도가 높은 키워드 (DB enum 형식)
    """
    sentence_embedding = get_embeddings(question)
    domain_embeddings = [get_embeddings(keyword) for keyword in domain_keywords]
    similarities = [
        (keyword, calculate_cosine_similarity(sentence_embedding, embedding)[0][0])
        for keyword, embedding in zip(domain_keywords, domain_embeddings)
    ]
    extracted_keyword = max(similarities, key=lambda x: x[1])[0]
    if extracted_keyword.lower() in ["people", "society"]:
        return "PeopleAndSociety"
    else:
        return extracted_keyword
