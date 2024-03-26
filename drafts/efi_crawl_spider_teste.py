import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
import xml.etree.ElementTree as ET

class EfiCrawlSpider(CrawlSpider):
    name = 'efi_crawl'
    allowed_domains = ['sejaefi.com.br']
    start_urls = ['https://sejaefi.com.br/blog/pix-o-que-e']

    custom_settings = {
        'DOWNLOAD_DELAY': 1,  
        'FEED_FORMAT': 'json', 
        'FEED_URI': 'output.json',  
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,  
        'RETRY_ENABLED': True,  
        'RETRY_TIMES': 2,  
        'USER_AGENT': 'EfiContentTrainer',  
    }

    rules = (
        Rule(LinkExtractor(deny=(r'/central-de-ajuda/'), allow=('pix',)), callback='parse_page', follow=False),
    )


    def parse_page(self, response):
        main_title_h1 = ''.join(response.xpath("//h1//text()").getall()).strip()
        description = response.xpath("//meta[@name='description']/@content").get(default='').strip()
        keywords = response.xpath("//meta[@name='keywords']/@content").get(default='').strip()
        
        text_content = response.xpath('//div[@id="menu"]/following-sibling::*[not(self::footer)]//text()').getall()
        text_content = [text.strip() for text in text_content if text.strip() != '']


        # Agora, vamos compilar todas essas informações em um único dicionário Python para ser yield.
        yield {
            'url': response.url,
            'title': response.css('title::text').get(default='').strip(),
            'main_title': main_title_h1,
            'description': description,
            'keywords': keywords,
            'content': text_content
        }
    def parse_start_url(self, response):
        return self.parse_page(response)