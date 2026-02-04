"""
Web scraper for Flipkart policy documents.
"""
import time
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logger import setup_logger
from app.core.models import PolicyDocument


logger = setup_logger(__name__)


class FlipkartPolicyScraper:
    """Scraper for Flipkart policy pages."""
    
    # Flipkart policy URLs (updated as needed)
    POLICY_URLS = {
        "returns": "https://www.flipkart.com/pages/returnpolicy",
        "shipping": "https://www.flipkart.com/pages/shippingpolicy",
        "cancellation": "https://www.flipkart.com/pages/cancellation",
        "terms": "https://www.flipkart.com/pages/terms",
        "privacy": "https://www.flipkart.com/pages/privacypolicy"
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.timeout = settings.SCRAPE_TIMEOUT
        self.delay = settings.SCRAPE_DELAY
    
    def _generate_policy_id(self, domain: str, url: str) -> str:
        """Generate unique policy ID."""
        content = f"{domain}_{url}_{datetime.utcnow().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove special characters
        text = text.replace('\xa0', ' ')
        text = text.replace('\u200b', '')
        return text.strip()
    
    def _extract_content(self, soup: BeautifulSoup) -> tuple[str, str]:
        """
        Extract raw and cleaned content from BeautifulSoup object.
        
        Returns:
            Tuple of (raw_content, cleaned_content)
        """
        # Extract raw HTML
        raw_content = str(soup)
        
        # Extract and clean text
        # Remove script and style elements
        for script in soup(["script", "style", "header", "footer", "nav"]):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator='\n')
        cleaned_content = self._clean_text(text)
        
        return raw_content, cleaned_content
    
    def scrape_policy(self, domain: str, url: str) -> Optional[PolicyDocument]:
        """
        Scrape a single policy page.
        
        Args:
            domain: Policy domain (returns, shipping, etc.)
            url: URL to scrape
        
        Returns:
            PolicyDocument or None if scraping fails
        """
        try:
            logger.info(f"Scraping {domain} policy from {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            title = title_tag.text if title_tag else f"{domain.title()} Policy"
            
            # Extract content
            raw_content, cleaned_content = self._extract_content(soup)
            
            # Create policy document
            policy_id = self._generate_policy_id(domain, url)
            
            policy_doc = PolicyDocument(
                policy_id=policy_id,
                policy_domain=domain,
                title=self._clean_text(title),
                source_url=url,
                raw_content=raw_content,
                cleaned_content=cleaned_content,
                scrape_timestamp=datetime.utcnow(),
                metadata={
                    "status_code": response.status_code,
                    "content_length": len(response.content)
                }
            )
            
            logger.info(f"Successfully scraped {domain} policy ({len(cleaned_content)} chars)")
            return policy_doc
            
        except Exception as e:
            logger.error(f"Failed to scrape {domain} from {url}: {str(e)}")
            return None
    
    def scrape_all_policies(self) -> List[PolicyDocument]:
        """
        Scrape all configured policy pages.
        
        Returns:
            List of PolicyDocument objects
        """
        policies = []
        
        for domain, url in self.POLICY_URLS.items():
            policy = self.scrape_policy(domain, url)
            
            if policy:
                policies.append(policy)
                self._save_policy(policy)
            
            # Delay between requests
            time.sleep(self.delay)
        
        logger.info(f"Scraping completed. Total policies: {len(policies)}")
        return policies
    
    def _save_policy(self, policy: PolicyDocument) -> None:
        """Save policy document to disk."""
        # Save raw content
        raw_path = settings.RAW_POLICIES_DIR / f"{policy.policy_id}.html"
        with open(raw_path, 'w', encoding='utf-8') as f:
            f.write(policy.raw_content)
        
        # Save cleaned content
        cleaned_path = settings.CLEANED_POLICIES_DIR / f"{policy.policy_id}.txt"
        with open(cleaned_path, 'w', encoding='utf-8') as f:
            f.write(policy.cleaned_content)
        
        # Save metadata
        meta_path = settings.CLEANED_POLICIES_DIR / f"{policy.policy_id}.json"
        metadata = {
            "policy_id": policy.policy_id,
            "policy_domain": policy.policy_domain,
            "title": policy.title,
            "source_url": policy.source_url,
            "scrape_timestamp": policy.scrape_timestamp.isoformat(),
            "metadata": policy.metadata
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved policy {policy.policy_id} to disk")
    
    def load_existing_policies(self) -> List[PolicyDocument]:
        """Load previously scraped policies from disk."""
        policies = []
        
        for meta_file in settings.CLEANED_POLICIES_DIR.glob("*.json"):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                policy_id = metadata['policy_id']
                
                # Load cleaned content
                cleaned_path = settings.CLEANED_POLICIES_DIR / f"{policy_id}.txt"
                with open(cleaned_path, 'r', encoding='utf-8') as f:
                    cleaned_content = f.read()
                
                # Load raw content
                raw_path = settings.RAW_POLICIES_DIR / f"{policy_id}.html"
                with open(raw_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                
                policy = PolicyDocument(
                    policy_id=policy_id,
                    policy_domain=metadata['policy_domain'],
                    title=metadata['title'],
                    source_url=metadata['source_url'],
                    raw_content=raw_content,
                    cleaned_content=cleaned_content,
                    scrape_timestamp=datetime.fromisoformat(metadata['scrape_timestamp']),
                    metadata=metadata.get('metadata', {})
                )
                
                policies.append(policy)
                
            except Exception as e:
                logger.error(f"Failed to load policy from {meta_file}: {str(e)}")
        
        logger.info(f"Loaded {len(policies)} existing policies from disk")
        return policies


def main():
    """Main function for standalone scraping."""
    scraper = FlipkartPolicyScraper()
    policies = scraper.scrape_all_policies()
    
    print(f"\n{'='*60}")
    print(f"Scraping Summary")
    print(f"{'='*60}")
    print(f"Total policies scraped: {len(policies)}")
    
    for policy in policies:
        print(f"\n{policy.policy_domain.upper()}:")
        print(f"  Title: {policy.title}")
        print(f"  URL: {policy.source_url}")
        print(f"  Content length: {len(policy.cleaned_content)} chars")
        print(f"  Policy ID: {policy.policy_id}")


if __name__ == "__main__":
    main()