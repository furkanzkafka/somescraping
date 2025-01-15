from telnetlib import EC

from selenium import webdriver
from selenium.webdriver.common.by import By
from urllib.parse import urljoin, urlparse
import csv
import time
import re

from selenium.webdriver.support.wait import WebDriverWait


class WebsiteEmailScraper:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-images')
        self.driver = webdriver.Chrome(options=options)
        self.visited_urls = set()

        # Define patterns
        self.excluded_patterns = [
            'wp-content', 'wp-includes', 'wp-admin',
            'blog', 'news', 'utility-pages', 'changelog',
            'styleguide', 'licenses', '.jpg', '.png', '.pdf',
            'tel:', 'javascript:', 'courses', 'start-here'
        ]

        self.priority_patterns = [
            'team', 'about', 'people', 'leadership',
            'contact', 'management', 'partners', 'executives', 'principals'
        ]

    def format_url(self, url):
        """Ensure URL has proper format with protocol"""
        if not url.startswith(('http://', 'https://')):
            return f'https://{url}'
        return url

    def is_valid_url(self, base_url, url):
        """Enhanced URL validation"""
        try:
            # Basic cleaning
            url = url.strip()
            base_domain = urlparse(base_url).netloc.replace('www.', '')
            url_domain = urlparse(url).netloc.replace('www.', '')

            # Check if internal link
            if not url_domain or url_domain == base_domain:
                # Check against excluded patterns
                if any(pattern in url.lower() for pattern in self.excluded_patterns):
                    return False

                # Remove query parameters and fragments
                clean_url = url.split('?')[0].split('#')[0]
                return True

            return False
        except:
            return False

    def extract_emails(self, text):
        """Extract email addresses from text"""
        if not text:
            return set()
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return set(re.findall(email_pattern, text))

    def get_page_emails(self, url):
        """Extract emails from a specific page"""
        try:
            self.driver.get(url)
            time.sleep(1)  # Give JavaScript time to load

            # Get visible text
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text

            # Get mailto links
            mailto_elements = self.driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
            mailto_emails = {href.get_attribute('href').replace('mailto:', '')
                             for href in mailto_elements if href.get_attribute('href')}

            # Look specifically for team/contact sections
            team_elements = self.driver.find_elements(
                By.XPATH,
                "//*[contains(@class, 'team') or contains(@class, 'contact') or \
                contains(@class, 'about') or contains(@id, 'team') or \
                contains(@id, 'contact') or contains(@id, 'people')]"
            )
            team_text = ' '.join(elem.text for elem in team_elements)

            # Combine all found emails
            all_emails = self.extract_emails(page_text)
            all_emails.update(mailto_emails)
            all_emails.update(self.extract_emails(team_text))

            if all_emails:
                print(f"Found emails on {url}: {all_emails}")

            return all_emails

        except Exception as e:
            print(f"Error accessing {url}: {str(e)}")
            return set()

    def get_page_links(self, url):
        """Get filtered links from page"""
        try:
            links = self.driver.find_elements(By.TAG_NAME, 'a')
            valid_links = set()
            priority_links = set()

            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and self.is_valid_url(url, href):
                        # Clean the URL
                        clean_url = href.split('?')[0].split('#')[0].rstrip('/')

                        # Check if it's a priority link
                        if any(pattern in clean_url.lower() for pattern in self.priority_patterns):
                            priority_links.add(clean_url)
                        else:
                            valid_links.add(clean_url)
                except:
                    continue

            return priority_links, valid_links
        except Exception as e:
            print(f"Error getting links from {url}: {str(e)}")
            return set(), set()

    def scrape_website(self, start_url):
        """Two-level crawling strategy"""
        print(f"\nProcessing website: {start_url}")
        start_url = self.format_url(start_url)
        all_emails = {}

        try:
            # First level: Get links from homepage
            self.driver.get(start_url)
            time.sleep(0.5)
            priority_links, regular_links = self.get_page_links(start_url)

            # Process homepage
            emails = self.get_page_emails(start_url)
            if emails:
                all_emails[start_url] = emails

            # Process priority links first
            print("Checking priority pages...")
            for url in priority_links:
                if url not in self.visited_urls:
                    print(f"Visiting priority page: {url}")
                    self.visited_urls.add(url)
                    emails = self.get_page_emails(url)
                    if emails:
                        all_emails[url] = emails

                    # If this is a team/about page, get sub-pages
                    if any(pattern in url.lower() for pattern in ['team', 'about', 'people', 'leadership']):
                        sub_priority, sub_regular = self.get_page_links(url)
                        for sub_url in sub_priority:
                            if sub_url not in self.visited_urls:
                                print(f"Visiting team member page: {sub_url}")
                                self.visited_urls.add(sub_url)
                                sub_emails = self.get_page_emails(sub_url)
                                if sub_emails:
                                    all_emails[sub_url] = sub_emails

                time.sleep(0.5)

            # Process remaining homepage links
            print("Checking regular pages...")
            for url in regular_links:
                if url not in self.visited_urls and url not in all_emails:
                    print(f"Visiting regular page: {url}")
                    self.visited_urls.add(url)
                    emails = self.get_page_emails(url)
                    if emails:
                        all_emails[url] = emails
                time.sleep(0.5)

            return all_emails

        except Exception as e:
            print(f"Error processing {start_url}: {str(e)}")
            return {}

    def scrape_multiple_websites(self, websites, output_file="found_emails.csv"):
        """Scrape multiple websites and save results to CSV"""
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Website', 'Page URL', 'Emails Found'])

                for website in websites:
                    print(f"\nProcessing website: {website}")
                    emails_by_page = self.scrape_website(website)

                    if emails_by_page:
                        for page_url, emails in emails_by_page.items():
                            writer.writerow([website, page_url, ', '.join(emails)])
                    else:
                        writer.writerow([website, 'N/A', 'No emails found'])

                    writer.writerow([])  # Empty row between websites

        finally:
            self.driver.quit()


# Example usage
if __name__ == "__main__":
    websites = [
        "examplesite.com",
        "examplesite2.com",
    ]

    scraper = WebsiteEmailScraper()
    scraper.scrape_multiple_websites(websites, "company_emails.csv")
