import scrapy
from scrapy_splash import SplashRequest
from scrapy.linkextractors import LinkExtractor

class EfiSpider(scrapy.Spider):
    name = 'efi_spider'
    allowed_domains = ['sejaefi.com.br']
    start_urls = ['https://sejaefi.com.br']

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'FEED_FORMAT': 'json',
        'FEED_URI': 'output-%(time)s.json',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 2,
        'USER_AGENT': 'EfiContentTrainer',
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
            yield SplashRequest(url, self.parse, args={'wait': 0.5})

    def parse(self, response):
        # Extrai e segue todos os links na página
        link_extractor = LinkExtractor(deny=('central-de-ajuda'))  # Exclui apenas links específicos
        links = link_extractor.extract_links(response)
        for link in links:
            yield SplashRequest(link.url, callback=self.parse, args={'wait': 0.5})
        
        # Extração de dados da página
        yield {
            'url': response.url,
            'title': response.css('title::text').get(default='').strip(),
            'main_title': ''.join(response.xpath("//h1//text()").getall()).strip(),
            'description': response.xpath("//meta[@name='description']/@content").get(default='').strip(),
            'keywords': response.xpath("//meta[@name='keywords']/@content").get(default='').strip(),
            'content': [text.strip() for text in response.xpath('//body//text()').getall() if text.strip() != '']
        }
