import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
import xml.etree.ElementTree as ET
from scrapy.exceptions import DropItem
import json
from datetime import datetime

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
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.file = open(f'output-pipeline-completo-{timestamp}.json', 'w')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item)) + "\n"
        self.file.write(line)
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
        }
    }

    rules = (
        Rule(LinkExtractor(deny=(r'central-de-ajuda', r'/blog')), callback='parse_page', follow=True),
    )

    def parse_page(self, response):
        self.logger.info(f'Processing page: {response.url}')
        yield EfiItem(
            url=response.url,
            title=response.css('title::text').get(default='').strip(),
            main_title=''.join(response.xpath("//h1//text()").getall()).strip(),
            description=response.xpath("//meta[@name='description']/@content").get(default='').strip(),
            keywords=response.xpath("//meta[@name='keywords']/@content").get(default='').strip(),
            content=[text.strip() for text in response.xpath('//div[@id="menu"]/following-sibling::*[not(self::footer)]//text()').getall() if text.strip() != '']
        )

if __name__ == '__main__':
    process = CrawlerProcess()
    process.crawl(EfiCrawlSpider)
    process.start()