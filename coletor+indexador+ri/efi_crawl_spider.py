import json
import math
import re
from collections import defaultdict
from datetime import datetime

# NLTK imports
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

# Spacy import
import spacy

# Scrapy imports
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import DropItem
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

# lxml and XML imports
from lxml import html, etree
from lxml.etree import ParserError
import xml.etree.ElementTree as ET

# Standard library imports
import os

nlp = spacy.load('pt_core_news_sm')

class EfiItem(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    main_title = scrapy.Field()
    description = scrapy.Field()
    keywords = scrapy.Field()
    content = scrapy.Field()


class ValidationPipeline:
    def process_item(self, item, spider):
        if not item.get('title') or not item.get('main_title'):
            raise DropItem("Missing title or main title in item.")
        # mais regras de validação aqui se necessário
        return item


class DataCleaningPipeline:
    def process_item(self, item, spider):
        if item.get('title'):
            item['title'] = item['title'].strip()
        # mais regras de limpeza conforme necessário aqui
        return item


class DuplicatesPipeline:
    def __init__(self):
        self.urls_seen = set()

    def process_item(self, item, spider):
        url = item['url']
        if url in self.urls_seen:
            raise DropItem(f"Duplicate item found: {url}")
        else:
            self.urls_seen.add(url)
            return item


class JsonWriterPipeline:
    def open_spider(self, spider):

        self.file_path = f'output-pipeline-completo.json'
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        
        self.file = open(self.file_path, 'w', encoding='utf-8')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False) + "\n"
        self.file.write(line)
        return item


class InvertedIndex:
    def __init__(self):
        self.index = defaultdict(dict)
        self.doc_count = 0
        self.doc_freq = defaultdict(int)

    def add_word(self, word, doc_id):
        if word not in self.index[doc_id]:
            self.index[doc_id][word] = 1
        else:
            self.index[doc_id][word] += 1
        self.doc_freq[word] += 1

    def calculate_tfidf(self):
        tfidf_index = defaultdict(dict)
        for doc_id, words in self.index.items():
            doc_len = len(words)
            for word, count in words.items():
                tf = count / float(doc_len)
                idf = math.log(self.doc_count / (1 + self.doc_freq[word]))
                tfidf_index[doc_id][word] = tf * idf
        return tfidf_index

class TfidfCalculationPipeline:
    def __init__(self):
        # Inicialização da pipeline; o spaCy já é inicializado externamente
        self.inverted_index = InvertedIndex()

    def open_spider(self, spider):
        # Preparar qualquer recurso quando a spider é aberta, se necessário
        self.inverted_index = InvertedIndex()

    def close_spider(self, spider):
        # Ao fechar a spider, calcular o TF-IDF e salvar em um arquivo
        self.tfidf_index = self.inverted_index.calculate_tfidf()
        with open('tfidf_index.json', 'w') as f:
            json.dump(self.tfidf_index, f, ensure_ascii=False)

    def preprocess(self, text):
        # Processamento do texto com o spaCy para tokenização, remoção de stopwords e lematização
        doc = nlp(text.lower())
        lemmatized_words = [token.lemma_ for token in doc if not token.is_stop and token.is_alpha]
        return lemmatized_words

    def process_item(self, item, spider):
        # Para cada item, incrementar a contagem de documentos, preprocessar o texto e adicionar palavras ao índice
        self.inverted_index.doc_count += 1
        text_content = ' '.join(item['content'])
        words = self.preprocess(text_content)
        for word in words:
            self.inverted_index.add_word(word, item['url'])
        return item


class EfiCrawlSpider(CrawlSpider):
    name = 'efi_crawl'
    allowed_domains = ['sejaefi.com.br']
    sitemap_urls = ['https://sejaefi.com.br/pages-sitemap.xml','https://sejaefi.com.br/formularios-sitemap.xml']

    def start_requests(self):
        for url in self.sitemap_urls:
            yield scrapy.Request(url, self.parse_sitemap)

    def parse_sitemap(self, response):
        root = ET.fromstring(response.text)
        for sitemap in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
            url = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text
            self.logger.info(f'Enqueueing URL from sitemap: {url}')
            yield scrapy.Request(url, self.parse_page)

    custom_settings = {
        'DOWNLOAD_DELAY': 1,  
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,  
        'RETRY_ENABLED': True,  
        'RETRY_TIMES': 2,  
        'USER_AGENT': 'EfiContentTrainer',  
        'ITEM_PIPELINES': {
            '__main__.DuplicatesPipeline': 100,
            '__main__.ValidationPipeline': 200,
            '__main__.DataCleaningPipeline': 300,            
            '__main__.JsonWriterPipeline': 400,
            '__main__.TfidfCalculationPipeline': 500
        }
    }

    rules = (
        Rule(LinkExtractor(deny=(r'central-de-ajuda', r'/blog')), callback='parse_page', follow=True),
    )

    def parse_page(self, response):
        self.logger.info(f'Processing page: {response.url}')
        try:
            # Parsear o HTML da resposta
            tree = html.fromstring(response.body)
            
            # Remover elementos <script> e <style>
            etree.strip_elements(tree, 'script', 'style', with_tail=False)
            
            # Remover o conteúdo do footer, se desejado
            footer = tree.xpath('//footer')
            for elem in footer:
                elem.getparent().remove(elem)
            
            # Extrair o texto do body, já limpo de <script> e <style>
            content = tree.xpath('//body//text()')
            # Filtrar e limpar o conteúdo
            content = [text.strip() for text in content if text.strip() != '']
            
            # Uso de expressões regulares para remover possíveis trechos indesejados remanescentes
            filtered_content = []
            for text in content:
                # Normalizar espaços
                text = re.sub(r'\s+', ' ', text)
                # Remover possíveis trechos inline de JavaScript/CSS que foram adicionados ao texto
                text = re.sub(r'(?s)<script.*?</script>', '', text)
                text = re.sub(r'(?s)<style.*?</style>', '', text)
                # Adicionar ao conteúdo filtrado se não for apenas caracteres de JS/CSS
                if text and not re.match(r'^[{};]+$', text):
                    filtered_content.append(text)
            
            # Gerar o item com o conteúdo filtrado
            yield EfiItem(
                url=response.url,
                title=response.css('title::text').get(default='').strip(),
                main_title=''.join(response.xpath("//h1//text()").getall()).strip(),
                description=response.xpath("//meta[@name='description']/@content").get(default='').strip(),
                keywords=response.xpath("//meta[@name='keywords']/@content").get(default='').strip(),
                content=filtered_content  # Aqui usamos o conteúdo já filtrado
            )
        except Exception as e:  # Usar Exception para uma captura mais ampla pode ser útil durante o desenvolvimento
            self.logger.error(f"Error parsing page {response.url}: {e}")




if __name__ == '__main__':
    process = CrawlerProcess()
    process.crawl(EfiCrawlSpider)
    process.start()