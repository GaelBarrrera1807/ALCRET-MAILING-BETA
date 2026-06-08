import ipaddress
import logging
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

INTERNAL_IPS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fd00::/8'),
    ipaddress.ip_network('fe80::/10'),
]


def _is_internal_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return True
        if host.lower() in ('localhost', 'localhost.localdomain'):
            return True
        if host.endswith('.local') or host.endswith('.internal'):
            return True
        ip = ipaddress.ip_address(host)
        return any(ip in net for net in INTERNAL_IPS)
    except (ValueError, TypeError):
        return True


class ScrapingService:
    def _fetch(self, url, timeout=15):
        if _is_internal_url(url):
            logger.warning(f'Blocked request to internal URL: {url}')
            raise requests.RequestException('URL interna bloqueada por seguridad')
        return requests.get(url, timeout=timeout, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }, allow_redirects=False)

    def _soup(self, url):
        response = self._fetch(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'lxml')

    def scrape_website(self, url):
        try:
            soup = self._soup(url)

            title = soup.title.string.strip() if soup.title else ''
            description = ''
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc['content'].strip()

            text = soup.get_text(separator=' ', strip=True)[:5000]

            emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))
            phones = set(re.findall(r'\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{2,4}[\s.-]?\d{2,4}', text))

            social_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if any(s in href.lower() for s in ['facebook.com', 'instagram.com', 'linkedin.com', 'twitter.com', 'youtube.com']):
                    social_links.append(href)

            return {
                'title': title,
                'description': description,
                'emails': list(emails),
                'phones': list(phones),
                'social_links': social_links[:10],
                'text_snippet': text[:1000],
            }
        except requests.RequestException as e:
            logger.error(f'Error scraping website {url}: {e}')
            return {'error': str(e)}
        except Exception as e:
            logger.error(f'Unexpected error scraping website {url}: {e}')
            return {'error': str(e)}

    def scrape_phone(self, company):
        try:
            sources = []
            if company.website:
                sources.append(company.website)
            if company.email:
                domain = company.email.split('@')[-1]
                sources.append(f'https://{domain}')

            all_phones = set()
            for source in sources[:3]:
                try:
                    soup = self._soup(source)
                    text = soup.get_text(separator=' ', strip=True)
                    phones = re.findall(
                        r'\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{2,4}[\s.-]?\d{2,4}',
                        text
                    )
                    all_phones.update(phones)
                except Exception:
                    continue

            return {
                'phones': list(all_phones)[:20],
                'sources_checked': sources[:3],
            }
        except Exception as e:
            logger.error(f'Error scraping phone for {company.name}: {e}')
            return {'error': str(e)}

    def scrape_social(self, company):
        try:
            social = {'facebook': '', 'instagram': '', 'linkedin': '', 'twitter': '', 'youtube': ''}
            sources = []

            if company.website:
                sources.append(company.website)
            if company.email:
                domain = company.email.split('@')[-1]
                sources.append(f'https://{domain}')

            for source in sources[:3]:
                try:
                    soup = self._soup(source)
                    for link in soup.find_all('a', href=True):
                        href = link['href'].lower()
                        for platform in social:
                            if f'{platform}.com' in href or f'{platform}.mx' in href:
                                if not social[platform]:
                                    social[platform] = link['href']
                except Exception:
                    continue

            return {
                'social_links': {k: v for k, v in social.items() if v},
                'sources_checked': sources[:3],
            }
        except Exception as e:
            logger.error(f'Error scraping social for {company.name}: {e}')
            return {'error': str(e)}

    def scrape_enrichment(self, company):
        try:
            sources = []
            if company.website:
                sources.append(company.website)
            if company.email:
                domain = company.email.split('@')[-1]
                sources.append(f'https://{domain}')

            result = {
                'description': '',
                'emails': [],
                'phones': [],
                'social_links': [],
                'address': '',
                'sources_checked': sources[:3],
            }

            for source in sources[:3]:
                try:
                    soup = self._soup(source)

                    text = soup.get_text(separator=' ', strip=True)[:5000]

                    if not result['description']:
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        if meta_desc and meta_desc.get('content'):
                            result['description'] = meta_desc['content'].strip()
                        elif soup.title:
                            result['description'] = soup.title.string.strip()

                    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                    result['emails'].extend(e for e in emails if e not in result['emails'])

                    phones = re.findall(
                        r'\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{2,4}[\s.-]?\d{2,4}',
                        text
                    )
                    result['phones'].extend(p for p in phones if p not in result['phones'])

                    for link in soup.find_all('a', href=True):
                        href = link['href'].lower()
                        if any(s in href for s in ['facebook.com', 'instagram.com', 'linkedin.com']):
                            if href not in result['social_links']:
                                result['social_links'].append(link['href'])

                    for script in soup.find_all('script', type='application/ld+json'):
                        import json
                        try:
                            ld = json.loads(script.string)
                            if isinstance(ld, dict):
                                if ld.get('address', {}).get('streetAddress'):
                                    result['address'] = ld['address']['streetAddress']
                        except Exception:
                            pass
                except Exception:
                    continue

            result['emails'] = result['emails'][:10]
            result['phones'] = result['phones'][:10]
            result['social_links'] = result['social_links'][:10]

            return result
        except Exception as e:
            logger.error(f'Error enriching {company.name}: {e}')
            return {'error': str(e)}
