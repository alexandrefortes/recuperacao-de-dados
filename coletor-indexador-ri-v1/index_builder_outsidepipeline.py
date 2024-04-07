import json
import math
from collections import defaultdict
import spacy

# Carregar o modelo de língua do SpaCy
nlp = spacy.load("pt_core_news_sm")

def preprocess(text):
    """Função para pré-processar o texto: tokenização, remoção de stopwords e lematização."""
    doc = nlp(text.lower())
    tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct and token.is_alpha]
    return tokens

def calculate_tfidf(documents):
    """Calcula o TF-IDF para cada termo em cada documento."""
    tf = defaultdict(lambda: defaultdict(int))
    df = defaultdict(int)
    N = len(documents)
    tfidf = defaultdict(dict)

    for doc_id, content in documents.items():
        processed_content = []
        for sentence in content:
            processed_content.extend(preprocess(sentence))
        unique_words = set(processed_content)
        for word in processed_content:
            tf[doc_id][word] += 1
        for word in unique_words:
            df[word] += 1

    for doc_id, words in tf.items():
        doc_len = sum(words.values())
        for word, freq in words.items():
            tf_value = freq / doc_len
            idf_value = math.log((N + 1) / (df[word] + 1)) + 1
            tfidf[doc_id][word] = tf_value * idf_value

    return tfidf

def read_and_preprocess(input_file):
    """Lê o arquivo de entrada e prepara os documentos."""
    documents = {}
    with open(input_file, 'r', encoding='utf-8') as file:
        for line in file:
            data = json.loads(line)
            documents[data['url']] = data['content']
    return documents

def main(input_file, output_file):
    """Processo principal para reconstruir o índice TF-IDF."""
    documents = read_and_preprocess(input_file)
    tfidf_index = calculate_tfidf(documents)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tfidf_index, f, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    input_file = 'output-pipeline-completo.json'
    output_file = 'tfidf_index_rebuilt.json'
    main(input_file, output_file)
