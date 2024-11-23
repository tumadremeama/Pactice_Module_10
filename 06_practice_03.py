

# -*- coding: utf-8 -*-

# Задача: проверить у какого сайта "тяжелее" главная страница.
# - получить html
# - узнать какие CSS и JS файлы нужны для отображения
# - подсчитать общий размер этих файлов
# - вывести на консоль результаты


#import multiprocessing

import multiprocessing
import requests
from bs4 import BeautifulSoup
from extractor import LinkExtractor
from utils import time_track


sites = [
    'https://www.fl.ru',
    'https://www.weblancer.net/',
    'https://www.freelancejob.ru/',
    'https://kwork.ru',
    'https://work-zilla.com/',
    'https://iklife.ru/udalennaya-rabota-i-frilans/poisk-raboty/vse-samye-luchshie-sajty-i-birzhi-v-internete.html',
]


class PageSizer(multiprocessing.Process):

    def __init__(self, url, collector, go_ahead=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.go_ahead = go_ahead
        self.total_bytes = 0
        self.collector = collector

    def run(self):
        self.total_bytes = 0
        html_data = self._get_html(url=self.url)
        
        if html_data is None:
            return
        self.total_bytes += len(html_data)
        
        if self.go_ahead:
            extractor = LinkExtractor(base_url=self.url)
            extractor.feed(html_data)
            
            css_js_links = self._get_css_js_links(html_data)
            for link in css_js_links:
                self.total_bytes += self._get_file_size(link)

            collector = multiprocessing.Queue()
            sizers = [PageSizer(url=link, go_ahead=False, collector=collector) for
                      link in extractor.links]
            for sizer in sizers:
                sizer.start()
            for sizer in sizers:
                sizer.join()
            while not collector.empty():
                data = collector.get()
                self.total_bytes += data['total_bytes']
        
        self.collector.put(dict(url=self.url, total_bytes=self.total_bytes))

    def _get_html(self, url):
        try:
            print(f'Go {url}...')
            res = requests.get(url)
            res.raise_for_status()
            return res.text
        except Exception as exc:
            print(f'Error fetching {url}: {exc}')
            return None
        
    def _get_css_js_links(self, html_data):
        soup = BeautifulSoup(html_data, 'html.parser')
        links = []
        
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                links.append(href)
                
        for script in soup.find_all('script'):
            src = script.get('src')
            if src:
                links.append(src)
                
        return links
    
    def _get_file_size(self, url):
        try:
            res = requests.head(url)
            return int(res.headers.get('Content-Length', 0))
        except Exception as exc:
            print(f'Error fetching file size for {url}: {exc}')
            return 0
        
        
@time_track
def main():
    collector = multiprocessing.Queue()
    sizers = [PageSizer(url=url, collector=collector) for url in sites]

    for sizer in sizers:
        sizer.start()
    for sizer in sizers:
        sizer.join()

    while not collector.empty():
        data = collector.get()
        print(f"For url {data['url']} need download {data['total_bytes']//1024} Kb ({data['total_bytes']} bytes)")


if __name__ == '__main__':
    main()
