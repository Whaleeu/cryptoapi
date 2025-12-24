"""
Crypto News Scraper - FastAPI Web Service
Provides REST API endpoint to scrape crypto news with configurable limit
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import requests
from bs4 import BeautifulSoup


app = FastAPI(
    title="Crypto News Scraper API",
    description="Scrape latest crypto news from crypto.news",
    version="1.0.0",
    root_path="/crypto"
)


class CryptoArticle(BaseModel):
    """Crypto Article model"""
    url: str
    title: str
    summary: Optional[str] = ""
    content: str
    date: Optional[str] = ""
    scraped_at: str


class CryptoScrapeResponse(BaseModel):
    """API response model"""
    success: bool
    articles: List[CryptoArticle]
    count: int
    scraped_at: str
    message: Optional[str] = None


def scrape_crypto_news(limit: int = 3):
    """
    Scrape crypto news from crypto.news - EXACT WORKING CODE from user
    
    Args:
        limit: Number of articles to scrape (1-20)
    
    Returns:
        List of articles or None if error
    """
    
    base_url = "https://crypto.news"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Step 1: Get article URLs from homepage
    article_urls = []
    try:
        response = requests.get(base_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the "latest" section
        latest_section = None
        
        # Strategy 1: Look for heading with "latest" text
        for heading in soup.find_all(['h1', 'h2', 'h3', 'div']):
            if heading.get_text().strip().lower() == 'latest':
                latest_section = heading.find_parent()
                break
        
        # Strategy 2: Look for section/div with class containing "latest"
        if not latest_section:
            latest_section = soup.find(['section', 'div'], class_=lambda x: x and 'latest' in x.lower())
        
        # Strategy 3: Look for articles after "latest" heading
        if not latest_section:
            for elem in soup.find_all(['h1', 'h2', 'h3']):
                if 'latest' in elem.get_text().lower():
                    latest_section = elem.find_next(['section', 'div', 'article'])
                    break
        
        # Extract article links from latest section
        if latest_section:
            for link in latest_section.find_all('a', href=True):
                url = link['href']
                
                # Build full URL
                if url.startswith('/'):
                    url = base_url + url
                
                # Filter valid article URLs
                if (base_url in url and 
                    url.count('/') >= 4 and
                    url not in article_urls and
                    not any(x in url for x in ['/category/', '/tag/', '/author/', '#', 
                                                '/buy-crypto/', '/events/', '/meme-coins/'])):
                    
                    article_urls.append(url)
                    
                    if len(article_urls) == limit:
                        break
    
    except Exception as e:
        raise Exception(f"Network error: {e}")
    
    # Check if we found articles
    if not article_urls:
        raise Exception("Could not find articles. Website structure may have changed.")
    
    # Step 2: Scrape each article
    articles = []
    
    for i, url in enumerate(article_urls, 1):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = ""
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
            
            # Extract content
            content_parts = []
            article_tag = soup.find('article')
            if article_tag:
                for p in article_tag.find_all('p'):
                    text = p.get_text(strip=True)
                    if len(text) > 50:
                        content_parts.append(text)
            
            content = '\n\n'.join(content_parts)
            
            # Extract summary
            summary = ""
            meta_desc = soup.find('meta', {'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                summary = meta_desc['content']
            
            # Extract date
            date = ""
            time_tag = soup.find('time')
            if time_tag:
                date = time_tag.get('datetime', '') or time_tag.get_text(strip=True)
            
            # Save article data
            article = {
                'url': url,
                'title': title,
                'summary': summary,
                'content': content,
                'date': date,
                'scraped_at': datetime.now().isoformat()
            }
            
            articles.append(article)
            
        except Exception as e:
            # Add partial article with error
            articles.append({
                'url': url,
                'title': 'Error fetching article',
                'summary': '',
                'content': f'Error: {str(e)[:200]}',
                'date': '',
                'scraped_at': datetime.now().isoformat()
            })
    
    # Check if we scraped any articles
    if not articles:
        raise Exception("No articles were scraped successfully")
    
    return articles


@app.get("/", tags=["Info"])
async def root():
    """API information"""
    return {
        "name": "Crypto News Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "/crypto-news": "GET - Fetch crypto news articles (param: limit=1-20)",
            "/api-status": "GET - Check API status"
        }
    }


@app.get("/api-status", tags=["Info"])
async def api_status():
    """API status check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Crypto News Scraper"
    }


@app.get("/crypto-news", response_model=CryptoScrapeResponse, tags=["Scraper"])
async def get_crypto_news(
    limit: int = Query(
        default=3,
        ge=1,
        le=20,
        description="Number of articles to fetch (1-20)"
    )
):
    """
    Fetch latest crypto news articles from crypto.news
    
    Parameters:
    - **limit**: Number of articles to fetch (1-20, default: 3)
    
    Returns:
    - List of scraped articles with title, summary, content, and URL
    """
    
    try:
        articles = scrape_crypto_news(limit)
        
        return CryptoScrapeResponse(
            success=True,
            articles=articles,
            count=len(articles),
            scraped_at=datetime.now().isoformat(),
            message=f"Successfully scraped {len(articles)} article(s)"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "message": "Failed to scrape articles. Check if the website is accessible."
            }
        )


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Crypto News Scraper API")
    print("="*60)
    print("\nStarting server...")
    print("API will be available at: http://localhost:8001")
    print("\nEndpoints:")
    print("  - http://localhost:8001/crypto-news?limit=5")
    print("  - http://localhost:8001/api-status")
    print("  - http://localhost:8001/docs (Interactive API documentation)")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)