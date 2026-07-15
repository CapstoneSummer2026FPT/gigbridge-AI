import os
import sys
import time
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base"

# Base API URL
FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1"

def crawl_website(url: str, collection_name: str = "general-knowledge", max_pages: int = 50, exclude_patterns: list = None):
    """
    Crawls a website using Firecrawl, extracts the main content in markdown format,
    and saves each page as a .md file inside the specified collection under knowledge-base/.
    """
    if exclude_patterns is None:
        exclude_patterns = [
            "/login", "/signup", "/cart", "/checkout", "/admin/*", 
            "/terms", "/privacy", "/cookie-policy", "/account/*",
            "/reset-password", "/forgot-password"
        ]
        
    headers = {
        "Content-Type": "application/json"
    }
    if FIRECRAWL_API_KEY:
        headers["Authorization"] = f"Bearer {FIRECRAWL_API_KEY}"
    else:
        print("Warning: FIRECRAWL_API_KEY not found in .env file.")
        print("Please set FIRECRAWL_API_KEY in gigbridge-AI/.env or export it as an environment variable.")
        
    print(f"Initiating crawl request for: {url}...")
    payload = {
        "url": url,
        "excludePaths": exclude_patterns,
        "scrapeOptions": {
            "formats": ["markdown"],
            "onlyMainContent": True
        }
    }
    
    if max_pages > 0:
        payload["limit"] = max_pages
        print(f"Applying page limit: {max_pages}")
    else:
        print("Running unlimited crawl (no page limit set)...")
        
    with httpx.Client() as client:
        try:
            response = client.post(f"{FIRECRAWL_API_URL}/crawl", json=payload, headers=headers, timeout=30.0)
            if response.status_code != 200:
                print(f"Error initiating crawl: Status {response.status_code} - {response.text}")
                return
            
            job_data = response.json()
            if not job_data.get("success"):
                print(f"Firecrawl crawl failed to start: {job_data}")
                return
                
            job_id = job_data.get("id")
            print(f"Crawl job started successfully! Job ID: {job_id}")
            
            status_url = f"{FIRECRAWL_API_URL}/crawl/{job_id}"
            while True:
                print("Checking crawl status...")
                status_resp = client.get(status_url, headers=headers, timeout=30.0)
                if status_resp.status_code != 200:
                    print(f"Error checking status: Status {status_resp.status_code} - {status_resp.text}")
                    time.sleep(10)
                    continue
                    
                status_data = status_resp.json()
                status = status_data.get("status")
                
                if status == "completed":
                    print("Crawl completed! Downloading data...")
                    pages = status_data.get("data", [])
                    save_pages(pages, collection_name)
                    break
                elif status == "failed":
                    print(f"Crawl job failed: {status_data.get('error')}")
                    break
                else:
                    completed_count = status_data.get("completed", 0)
                    total_count = status_data.get("total", 0)
                    print(f"Crawl status: {status} ({completed_count}/{total_count} pages crawled). Waiting...")
                    time.sleep(10)
                    
        except httpx.RequestError as exc:
            print(f"An error occurred while requesting: {exc}")

def batch_scrape_website(base_url: str, collection_name: str = "general-knowledge"):
    """
    Scrapes all known public sub-pages of the target website individually
    using Firecrawl's /scrape API. This bypasses client-side React Router navigation.
    """
    sub_paths = [
        "",
        "about",
        "careers",
        "faq",
        "press-kit",
        "guide",
        "market-insights"
    ]
    
    headers = {
        "Content-Type": "application/json"
    }
    if FIRECRAWL_API_KEY:
        headers["Authorization"] = f"Bearer {FIRECRAWL_API_KEY}"
    else:
        print("Error: FIRECRAWL_API_KEY is required for scraping.")
        return
        
    base_url = base_url.rstrip("/")
    pages_data = []
    
    with httpx.Client() as client:
        for path in sub_paths:
            target_url = f"{base_url}/{path}" if path else base_url
            print(f"Scraping page: {target_url}...")
            
            payload = {
                "url": target_url,
                "formats": ["markdown"],
                "onlyMainContent": True,
                "actions": [
                    {
                        "type": "wait",
                        "milliseconds": 5000
                    }
                ]
            }
            
            try:
                response = client.post(f"{FIRECRAWL_API_URL}/scrape", json=payload, headers=headers, timeout=60.0)
                if response.status_code != 200:
                    print(f"Error scraping {target_url}: Status {response.status_code} - {response.text}")
                    continue
                    
                result = response.json()
                if not result.get("success"):
                    print(f"Failed to scrape {target_url}: {result}")
                    continue
                    
                data = result.get("data", {})
                pages_data.append(data)
                print(f"Successfully scraped: {target_url}")
                
            except Exception as e:
                print(f"Exception while scraping {target_url}: {e}")
                
            # Add a small delay between requests to be polite
            time.sleep(2)
            
    if pages_data:
        save_pages(pages_data, collection_name)
    else:
        print("No pages successfully scraped in batch mode.")

def save_pages(pages, collection_name: str):
    """
    Saves crawled pages into the designated collection directory.
    """
    target_dir = KNOWLEDGE_BASE_PATH / collection_name
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Saving crawled pages to {target_dir}...")
    saved_count = 0
    
    for page in pages:
        markdown = page.get("markdown", "")
        metadata = page.get("metadata", {})
        
        # Determine source url and clean title for filename
        source_url = metadata.get("sourceURL") or metadata.get("url") or ""
        title = metadata.get("title") or ""
        
        if not markdown.strip():
            continue
            
        # Clean title for file name
        safe_title = "".join([c if c.isalnum() or c in "-_" else "_" for c in title]).strip("_")
        if not safe_title:
            # Fallback to URL path segment
            safe_title = source_url.split("/")[-1] or "page"
            safe_title = "".join([c if c.isalnum() or c in "-_" else "_" for c in safe_title]).strip("_")
            
        # Ensure name isn't too long
        safe_title = safe_title[:50]
        file_name = f"{safe_title}.md"
        file_path = target_dir / file_name
        
        # Check if file exists, append count if so
        counter = 1
        while file_path.exists():
            file_name = f"{safe_title}_{counter}.md"
            file_path = target_dir / file_name
            counter += 1
            
        # Add YAML frontmatter to the top of the markdown file for the ingestion pipeline
        metadata_header = f"""---
title: "{title}"
source: "{source_url}"
description: "{metadata.get('description', '')}"
---

"""
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(metadata_header + markdown)
            print(f"Saved: {file_name} (Source: {source_url})")
            saved_count += 1
        except Exception as e:
            print(f"Error saving {file_name}: {e}")
            
    print(f"\nSuccessfully saved {saved_count} pages.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python crawl_website.py <URL_to_crawl> [collection_name] [max_pages_or_flag]")
        print("Example: python crawl_website.py https://gigbridge.id.vn/ general-knowledge 0")
        print("Example for Batch Mode: python crawl_website.py https://gigbridge.id.vn/ general-knowledge --batch")
        sys.exit(1)
        
    target_url = sys.argv[1]
    col = sys.argv[2] if len(sys.argv) > 2 else "general-knowledge"
    
    flag = sys.argv[3] if len(sys.argv) > 3 else "0"
    if flag == "--batch":
        batch_scrape_website(target_url, col)
    else:
        limit = int(flag)
        crawl_website(target_url, col, limit)
