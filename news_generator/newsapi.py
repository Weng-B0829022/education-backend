import json
import requests
from newspaper import Article
from typing import Dict, Any
from datetime import datetime, timedelta


API_KEY = 'a515d699b0eb4a09b3a0560df37f6074'
BASE_URL = 'https://newsapi.org/v2'


class NewsAPI:
    def __init__(self) -> None:
        self.total_articles = 0
        self.MAX_ARTICLES= 20
        self.categories = [
            'business',
            'entertainment',
            'general',
            'health',
            'science',
            'sports',
            'technology'
        ]
        self.domains = []

    def get_everything(self, keyword, date) -> Dict[str, Any]:
        print(f"正在搜尋關鍵字 '{keyword}' 的新聞...")
        url = (
            f'{BASE_URL}/everything?'               #API路徑
            f'apiKey={API_KEY}&'                    #API金鑰
            f'q={keyword}&'                         #關鍵字
            #f'domains={",".join(self.domains)}&'   #網域
            f'sortBy=popularity&'                   #排序方式
            f'language=zh&'                         #語言
            f'pageSize=20'                          #每頁數量
        )
        
        response = requests.get(url)
        result = json.loads(response.text)
        self.total_articles = len(result.get('articles', []))
        print(f"找到 {self.total_articles} 篇相關新聞")
        
        with open('article_urls.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(keyword)
        if self.total_articles == 0:
            return {}
        return result

    def get_top_headlines(self, category: str, country: str) -> Dict[str, Any]:
        print(f"正在獲取 {country} 地區 {category} 類別的頭條新聞...")
        url = (
            f'{BASE_URL}/top-headlines?'
            f'apiKey={API_KEY}&'
            f'category={category}&'
            f'pageSize=100&'
            f'country={country}'
        )

        response = requests.get(url)
        result = json.loads(response.text)
        articles_count = len(result.get('articles', []))
        print(f"{category} 類別找到 {articles_count} 篇新聞")
        return result

    def get_all_top_headlines(self, country: str) -> Dict[str, Any]:
        print(f"開始獲取 {country} 地區所有類別的頭條新聞...")
        all_top_headlines = {}
        self.total_articles = 0
        
        for i, category in enumerate(self.categories, 1):
            print(f"正在處理第 {i}/{len(self.categories)} 個類別: {category}")
            top_headlines = self.get_top_headlines(category, country)
            all_top_headlines[category] = top_headlines
            self.total_articles += len(top_headlines.get('articles', []))

        print(f"完成所有類別搜索，共找到 {self.total_articles} 篇新聞")
        return all_top_headlines

    def __fetch_article_content(self, url: str) -> str:
        print(f"正在解析文章內容: {url}")
        article = Article(url)
        article.download()
        article.parse()
        return article.text

    def __normalize_articles(self, articles: Dict[str, str]) -> Dict[str, str]:
        normalized_data = []
        processed_count = 0
        success_count = 0
        
        for category in articles.values():
            if success_count >= self.MAX_ARTICLES:
                break
                
            for article in category.get('articles', []):
                if success_count >= self.MAX_ARTICLES:
                    break
                    
                processed_count += 1
                print(f"正在處理第 {processed_count} 篇文章 (成功: {success_count})")
                
                try:
                    content = self.__fetch_article_content(article.get('url'))
                    if not content:  # Skip if content is empty
                        print(f"跳過空內容文章: {article.get('title')}")
                        continue
                        
                    normalized_article = {
                        'title': article.get('title'),
                        'published_at': article.get('publishedAt'),
                        'url': article.get('url'),
                        'content': content
                    }
                    normalized_data.append(normalized_article)
                    success_count += 1
                    print(f"成功解析文章: {article.get('title')}")
                    
                except Exception as e:
                    print(f"解析文章失敗 {article.get('url')}: {str(e)}")
                    continue

        print(f"文章處理完成 - 總處理: {processed_count}, 成功: {success_count}")
        return normalized_data

    def get_taiwan_news(self) -> Dict[str, Any]:
        print("開始獲取台灣新聞...")
        all_top_headlines = self.get_all_top_headlines('tw')
        print("開始解析台灣新聞內容...")
        normalized_articles = self.__normalize_articles(all_top_headlines)
        print("台灣新聞處理完成")
        return normalized_articles

    def get_international_news(self) -> Dict[str, Any]:
        print("開始獲取國際新聞...")
        all_top_headlines = self.get_all_top_headlines('us')
        print("開始解析國際新聞內容...")
        normalized_articles = self.__normalize_articles(all_top_headlines)
        print("國際新聞處理完成")
        return normalized_articles

    def get_keyword_taiwan_news(self, keyword, date) -> Dict[str, Any]:
        print(f"開始搜尋關鍵字 '{keyword}' 的台灣新聞...")
        everything = self.get_everything(keyword, date)
        keyword_taiwan_news = { 'everything': everything }
        print(keyword_taiwan_news)
        if not keyword_taiwan_news:
            print(f"未找到關鍵字 '{keyword}' 的台灣新聞")
            return {}
        print("開始解析關鍵字新聞內容...")
        normalized_articles = self.__normalize_articles(keyword_taiwan_news)
        print(f"關鍵字 '{keyword}' 新聞處理完成")
        return normalized_articles


def run_newsapi(keyword):
    print(f"=== 開始執行 NewsAPI 搜索 ===")
    print(f"關鍵字: {keyword}")
    
    news_api = NewsAPI()
    date_7_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    print(f"搜索日期範圍: {date_7_days_ago} 至今")
    
    keyword_taiwan_news = news_api.get_keyword_taiwan_news(keyword, date_7_days_ago)
    return keyword_taiwan_news
