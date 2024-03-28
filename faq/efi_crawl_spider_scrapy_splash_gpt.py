import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy_splash import SplashRequest
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.exceptions import DropItem
import json
from datetime import datetime
from lxml import etree

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
            raise DropItem("Missing title or main_title in item.")
        return item

class DataCleaningPipeline:
    def process_item(self, item, spider):
        item['title'] = item.get('title', '').strip()
        return item

class DuplicatesPipeline:
    def __init__(self):
        self.urls_seen = set()

    def process_item(self, item, spider):
        if item['url'] in self.urls_seen:
            raise DropItem(f"Duplicate item found: {item['url']}")
        else:
            self.urls_seen.add(item['url'])
            return item

class JsonWriterPipeline:
    def open_spider(self, spider):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.file = open(f'output-com-splash-{timestamp}.json', 'w')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False) + "\n"
        self.file.write(line)
        return item

class EfiCrawlSpider(CrawlSpider):
    name = 'efi_crawl'
    allowed_domains = ['sejaefi.com.br']
    start_urls = ['https://sejaefi.com.br/']

    rules = (
        Rule(LinkExtractor(allow=(), deny=()), callback='parse_item', follow=True),
    )

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
        },
        'SPLASH_URL': 'http://localhost:8050',
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'SPIDER_MIDDLEWARES': {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
    }

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(url, self.parse_item, endpoint='execute', args={
                'lua_source': """
                function main(splash, args)
                    splash:go(args.url)
                    splash:wait(5)
                    return {html = splash:html()}
                end
                """
            })

    def parse_item(self, response):
        # Processamento da página alvo
        self.logger.info(f'Now processing: {response.url}')

        item = EfiItem()
        item['url'] = response.url
        item['title'] = response.css('title::text').get(default='').strip()
        item['main_title'] = ''.join(response.xpath("//h1//text()").getall()).strip()
        item['description'] = response.xpath("//meta[@name='description']/@content").get(default='').strip()
        item['keywords'] = response.xpath("//meta[@name='keywords']/@content").get(default='').strip()
        item['content'] = [text.strip() for text in response.xpath('//body//*[not(self::script or self::style)]/text()').getall() if text.strip() != '']
        yield item

if __name__ == '__main__':
    process = CrawlerProcess()
    process.crawl(EfiCrawlSpider)
    process.start()