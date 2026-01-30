from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse


# Standard headers to fetch a website
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}


def fetch_website_contents(url):
    """
    Return the title and contents of the website at the given url;
    truncate to 2,000 characters as a sensible limit
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.string if soup.title else "No title found"
        
        if soup.body:
            for irrelevant in soup.body(["script", "style", "img", "input"]):
                irrelevant.decompose()
            text = soup.body.get_text(separator="\n", strip=True)
        else:
            text = ""
        
        return (title + "\n\n" + text)[:2_000]
    
    except requests.exceptions.ConnectionError as e:
        # This catches DNS errors, connection refused, etc.
        print(f"Connection Error: Could not connect to {url}")
        return f"[Error: Could not connect to {url}]"
    
    except requests.exceptions.Timeout:
        print(f"Timeout Error: {url} took too long to respond")
        return f"[Error: Timeout for {url}]"
    
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error {e.response.status_code}: {url}")
        return f"[Error: HTTP {e.response.status_code} for {url}]"
    
    except requests.exceptions.RequestException as e:
        # Catch-all for any other requests errors
        print(f"Request Error: {url} - {str(e)[:200]}")
        return f"[Error: Could not fetch {url}]"
    
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected Error: {url} - {str(e)[:200]}")
        return f"[Error: Unexpected error for {url}]"


def fetch_website_links(url):
    """
    Return the links on the website at the given url
    I realize this is inefficient as we're parsing twice! This is to keep the code in the lab simple.
    Feel free to use a class and optimize it!
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        links = []
        
        for link in soup.find_all("a"):
            href = link.get("href")
            if href:
                # Convert relative URLs to absolute URLs
                absolute_url = urljoin(url, href)
                links.append(absolute_url)
        
        return links
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching links from {url}: {str(e)[:100]}")
        return []
    except Exception as e:
        print(f"Unexpected error fetching links from {url}: {str(e)[:100]}")
        return []


# BONUS: More efficient combined version
class WebsiteFetcher:
    """
    Fetch a website once and extract both content and links efficiently
    """
    
    def __init__(self, url):
        self.url = url
        self.soup = None
        self._fetch()
    
    def _fetch(self):
        """Fetch and parse the website once"""
        try:
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
            self.soup = BeautifulSoup(response.content, "html.parser")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {self.url}: {str(e)[:100]}")
            self.soup = None
    
    def get_contents(self, max_length=2000):
        """Extract title and text content"""
        if not self.soup:
            return f"[Error: Could not fetch {self.url}]"
        
        title = self.soup.title.string if self.soup.title else "No title found"
        
        if self.soup.body:
            # Create a copy to avoid modifying the original
            body_copy = BeautifulSoup(str(self.soup.body), "html.parser")
            for irrelevant in body_copy(["script", "style", "img", "input"]):
                irrelevant.decompose()
            text = body_copy.get_text(separator="\n", strip=True)
        else:
            text = ""
        
        return (title + "\n\n" + text)[:max_length]
    
    def get_links(self):
        """Extract all links"""
        if not self.soup:
            return []
        
        links = []
        for link in self.soup.find_all("a"):
            href = link.get("href")
            if href:
                absolute_url = urljoin(self.url, href)
                links.append(absolute_url)
        
        return links


# Example usage of the efficient version:
# fetcher = WebsiteFetcher("https://example.com")
# contents = fetcher.get_contents()
# links = fetcher.get_links()