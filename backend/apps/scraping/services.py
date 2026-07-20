import ipaddress
import json
import logging
import re
import time
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx
import requests
from bs4 import BeautifulSoup
from django.conf import settings

from apps.core.models import Company, CompanyContact
from apps.scraping.models import ScrapingJob, ScrapedData

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

    def _fetch(self, url: str, timeout: int = 15) -> requests.Response:
        if _is_internal_url(url):
            logger.warning(f'Blocked request to internal URL: {url}')
            raise requests.RequestException('URL interna bloqueada por seguridad')
        return requests.get(
            url,
            timeout=timeout,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
            },
            allow_redirects=False,
        )

    def _soup(self, url: str) -> BeautifulSoup:
        response = self._fetch(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'lxml')

    def scrape_website(self, url: str) -> Dict[str, Any]:
        try:
            soup = self._soup(url)

            title = soup.title.string.strip() if soup.title else ''
            description = ''
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc['content'].strip()

            text = soup.get_text(separator=' ', strip=True)[:5000]

            emails = set(
                re.findall(
                    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text
                )
            )
            phones = set(
                re.findall(
                    r'\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{2,4}[\s.-]?\d{2,4}',
                    text,
                )
            )

            social_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if any(
                    s in href.lower()
                    for s in [
                        'facebook.com',
                        'instagram.com',
                        'linkedin.com',
                        'twitter.com',
                        'youtube.com',
                    ]
                ):
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

    def scrape_phone(self, company: Company) -> Dict[str, Any]:
        try:
            sources: List[str] = []
            if company.website:
                sources.append(company.website)
            if company.email:
                domain = company.email.split('@')[-1]
                sources.append(f'https://{domain}')

            all_phones: set = set()
            for source in sources[:3]:
                try:
                    soup = self._soup(source)
                    text = soup.get_text(separator=' ', strip=True)
                    phones = re.findall(
                        r'\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{2,4}[\s.-]?\d{2,4}',
                        text,
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

    def scrape_social(self, company: Company) -> Dict[str, Any]:
        try:
            social = {
                'facebook': '',
                'instagram': '',
                'linkedin': '',
                'twitter': '',
                'youtube': '',
            }
            sources: List[str] = []

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

    def scrape_enrichment(self, company: Company) -> Dict[str, Any]:
        try:
            sources: List[str] = []
            if company.website:
                sources.append(company.website)
            if company.email:
                domain = company.email.split('@')[-1]
                sources.append(f'https://{domain}')

            result: Dict[str, Any] = {
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

                    emails = re.findall(
                        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text
                    )
                    result['emails'].extend(
                        e for e in emails if e not in result['emails']
                    )

                    phones = re.findall(
                        r'\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{2,4}[\s.-]?\d{2,4}',
                        text,
                    )
                    result['phones'].extend(
                        p for p in phones if p not in result['phones']
                    )

                    for link in soup.find_all('a', href=True):
                        href = link['href'].lower()
                        if any(
                            s in href
                            for s in ['facebook.com', 'instagram.com', 'linkedin.com']
                        ):
                            if href not in result['social_links']:
                                result['social_links'].append(link['href'])

                    for script in soup.find_all('script', type='application/ld+json'):
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

    def run_external_scraping(self, job_id: str) -> Dict[str, Any]:
        try:
            job = ScrapingJob.objects.prefetch_related('companies').get(id=job_id)
        except ScrapingJob.DoesNotExist:
            raise ValueError(f'ScrapingJob {job_id} no encontrado')

        job.status = 'processing'
        job.save(update_fields=['status'])
        logger.info(f'ScrapingJob {job_id} cambiado a processing')

        if job.job_type not in ('social', 'enrichment'):
            raise ValueError(
                f'run_external_scraping solo soporta social/enrichment, '
                f'got {job.job_type}'
            )

        apify_key: str = getattr(settings, 'APIFY_API_KEY', '')

        if not apify_key:
            raise RuntimeError(
                'APIFY_API_KEY no configurado en settings del proyecto'
            )

        company = job.companies.first()
        company_name: str = company.name if company else ''
        target_url: str = job.url or (company.website if company else '')

        apify_actor_id: str = getattr(
            settings,
            'APIFY_ACTOR_ID',
            'apify~linkedin-sales-navigator-scraper',
        )

        apify_contacts: List[Dict[str, Any]] = []
        snov_raw: Dict[str, Any] = {}

        with httpx.Client(timeout=30.0) as client:
            run_response = client.post(
                f'https://api.apify.com/v2/acts/{apify_actor_id}/runs',
                params={'token': apify_key},
                json={
                    'companyUrls': [target_url] if target_url else [],
                    'companyName': company_name,
                },
            )
            run_response.raise_for_status()
            run_data: Dict[str, Any] = run_response.json().get('data', {})
            run_id: str = run_data.get('id', '')

            if not run_id:
                raise RuntimeError(
                    'Apify no devolvió un run ID al iniciar el actor'
                )

            max_attempts: int = 30
            for attempt in range(max_attempts):
                status_response = client.get(
                    f'https://api.apify.com/v2/actor-runs/{run_id}',
                    params={'token': apify_key},
                )
                status_response.raise_for_status()
                status: str = status_response.json().get('data', {}).get('status', '')

                if status == 'SUCCEEDED':
                    logger.info(
                        f'Apify run {run_id} completado exitosamente '
                        f'tras {attempt + 1} intentos'
                    )
                    break
                elif status in ('FAILED', 'TIMED-OUT', 'ABORTED'):
                    raise RuntimeError(
                        f'Apify run {run_id} terminó con estado: {status}'
                    )

                time.sleep(5)
            else:
                raise TimeoutError(
                    f'Apify run {run_id} no completó dentro de '
                    f'{max_attempts * 5}s'
                )

            results_response = client.get(
                f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items',
                params={'token': apify_key},
            )
            results_response.raise_for_status()
            apify_contacts = results_response.json()

            if not isinstance(apify_contacts, list):
                apify_contacts = []

            snov_client_id: str = getattr(settings, 'SNOV_CLIENT_ID', '')
            snov_client_secret: str = getattr(settings, 'SNOV_CLIENT_SECRET', '')
            access_token: str = ''

            if snov_client_id and snov_client_secret:
                try:
                    token_response = client.post(
                        'https://api.snov.io/v1/oauth/access_token',
                        json={
                            'client_id': snov_client_id,
                            'client_secret': snov_client_secret,
                        },
                    )
                    token_response.raise_for_status()
                    token_data = token_response.json()
                    access_token = token_data.get('access_token', '')
                    logger.info('Snov.io OAuth token obtenido exitosamente')
                except Exception as e:
                    logger.warning(f'Snov.io OAuth falló: {e}')

            for contact in apify_contacts:
                linkedin_url: str = (contact.get('linkedinUrl') or '').strip()
                if not linkedin_url:
                    continue

                if contact.get('email'):
                    continue

                if not access_token:
                    continue

                full_name: str = (contact.get('fullName') or '').strip()
                if not full_name:
                    continue

                name_parts: List[str] = full_name.split(' ', 1)
                first_name: str = name_parts[0]
                last_name: str = name_parts[1] if len(name_parts) > 1 else ''

                parsed_domain = urlparse(target_url).netloc
                if parsed_domain.startswith('www.'):
                    parsed_domain = parsed_domain[4:]
                if not parsed_domain:
                    continue

                try:
                    profile_response = client.post(
                        'https://api.snov.io/v1/get-profile-by-name-and-domain',
                        headers={'Authorization': f'Bearer {access_token}'},
                        json={
                            'firstName': first_name,
                            'lastName': last_name,
                            'domain': parsed_domain,
                        },
                    )
                    profile_response.raise_for_status()
                    profile_data: Dict[str, Any] = profile_response.json()

                    snov_raw[linkedin_url] = profile_data

                    email_found: str = profile_data.get('email', '')
                    if email_found:
                        contact['email'] = email_found
                except httpx.HTTPStatusError as e:
                    logger.warning(
                        f'Snov.io enrichment falló para {linkedin_url}: '
                        f'{e.response.status_code} - {e.response.text[:200]}'
                    )
                except Exception as e:
                    logger.warning(
                        f'Error inesperado en Snov.io para {linkedin_url}: {e}'
                    )

        clean_data: Dict[str, Any] = {
            'contacts': [
                {
                    'name': c.get('fullName', ''),
                    'title': c.get('title', ''),
                    'linkedin_url': c.get('linkedinUrl', ''),
                    'company_name': c.get('companyName', ''),
                    'email': c.get('email', ''),
                    'phone': c.get('phone', ''),
                }
                for c in apify_contacts
                if c.get('fullName')
            ],
            'source': 'apify_snov',
        }

        combined_raw: Dict[str, Any] = {
            'apify_contacts': apify_contacts,
            'snov_enrichments': snov_raw,
            'apify_run_id': run_id,
        }

        ScrapedData.objects.create(
            company=company,
            source='apify',
            data_type='external_api',
            raw_data=combined_raw,
        )
        logger.info(
            f'ScrapedData guardado para company={company.id if company else None}, '
            f'job={job_id}'
        )

        return clean_data

    GOOGLE_MAPS_ACTOR_ID = 'compass~crawler-google-places'

    def discover_from_google_maps(
        self, search_query: str, location: str, limit: int = 50
    ) -> Dict[str, Any]:
        apify_key: str = getattr(settings, 'APIFY_API_KEY', '')
        if not apify_key:
            raise RuntimeError('APIFY_API_KEY no configurado en settings del proyecto')

        search_string = f'{search_query} {location}'.strip()
        logger.info(
            'Iniciando descubrimiento Google Maps: '
            f'query="{search_string}", limit={limit}'
        )

        with httpx.Client(timeout=30.0) as client:
            run_response = client.post(
                f'https://api.apify.com/v2/acts/{self.GOOGLE_MAPS_ACTOR_ID}/runs',
                params={'token': apify_key},
                json={
                    'searchString': search_string,
                    'maxCrawledPlaces': limit,
                    'proxyConfig': {'useApifyProxy': True},
                },
            )
            run_response.raise_for_status()
            run_data: Dict[str, Any] = run_response.json().get('data', {})
            run_id: str = run_data.get('id', '')
            if not run_id:
                raise RuntimeError(
                    'Apify Google Maps no devolvió un run ID'
                )

            max_attempts: int = 150
            for attempt in range(max_attempts):
                status_response = client.get(
                    f'https://api.apify.com/v2/actor-runs/{run_id}',
                    params={'token': apify_key},
                )
                status_response.raise_for_status()
                status: str = status_response.json().get('data', {}).get('status', '')
                if status == 'SUCCEEDED':
                    logger.info(
                        f'Apify Google Maps run {run_id} completado '
                        f'tras {attempt + 1} intentos'
                    )
                    break
                elif status in ('FAILED', 'TIMED-OUT', 'ABORTED'):
                    raise RuntimeError(
                        f'Apify Google Maps run {run_id} terminó con: {status}'
                    )
                import time
                time.sleep(4)
                if attempt > 0 and attempt % 15 == 0:
                    logger.info(
                        f'Apify Google Maps run {run_id} aún en progreso '
                        f'(intento {attempt + 1}/{max_attempts})'
                    )
            else:
                raise TimeoutError(
                    f'Apify Google Maps run {run_id} no completó en '
                    f'{max_attempts * 4}s'
                )

            results_response = client.get(
                f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items',
                params={'token': apify_key},
            )
            results_response.raise_for_status()
            results: List[Dict[str, Any]] = results_response.json()
            if not isinstance(results, list):
                results = []

        logger.info(
            f'Google Maps devolvió {len(results)} resultados para '
            f'"{search_string}"'
        )
        return {
            'search_query': search_query,
            'location': location,
            'run_id': run_id,
            'results': results,
        }

    def _snovio_get_token(self, client: httpx.Client) -> str:
        snov_client_id: str = getattr(settings, 'SNOV_CLIENT_ID', '')
        snov_client_secret: str = getattr(settings, 'SNOV_CLIENT_SECRET', '')
        if not snov_client_id or not snov_client_secret:
            logger.warning('SNOV_CLIENT_ID o SNOV_CLIENT_SECRET no configurados')
            return ''
        try:
            token_response = client.post(
                'https://api.snov.io/v1/oauth/access_token',
                json={
                    'client_id': snov_client_id,
                    'client_secret': snov_client_secret,
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get('access_token', '')
            if access_token:
                logger.info('Snov.io OAuth token obtenido exitosamente')
            return access_token
        except Exception as e:
            logger.warning(f'Snov.io OAuth falló: {e}')
            return ''

    def fetch_contacts_by_domain(
        self, domain: str, position_keywords: List[str] = None
    ) -> Dict[str, Any]:
        if not domain:
            return {'contacts': [], 'error': 'Dominio vacío'}
        if position_keywords is None:
            position_keywords = [
                'logistica', 'operaciones', 'compras', 'finanzas',
                'cfo', 'director', 'gerente', 'dueno', 'owner',
            ]
        logger.info(f'Snov.io: buscando contactos para dominio "{domain}"')
        try:
            with httpx.Client(timeout=30.0) as client:
                access_token = self._snovio_get_token(client)
                if not access_token:
                    return {'contacts': [], 'error': 'Snov.io no autenticado'}

                all_matches: List[Dict[str, str]] = []
                last_id: int = 0
                max_pages: int = 5

                for page in range(max_pages):
                    response = client.post(
                        'https://api.snov.io/v2/domain-emails',
                        headers={'Authorization': f'Bearer {access_token}'},
                        json={
                            'domain': domain,
                            'limit': 100,
                            'lastId': last_id,
                        },
                    )
                    response.raise_for_status()
                    body = response.json()
                    items = body.get('result', []) or body.get('data', []) or []
                    total = body.get('total', 0) or len(items)

                    if not isinstance(items, list):
                        items = []

                    for item in items:
                        position = (
                            item.get('position') or item.get('jobTitle') or ''
                        ).strip().lower()
                        if not position:
                            continue
                        if any(kw in position for kw in position_keywords):
                            all_matches.append({
                                'first_name': item.get('firstName', ''),
                                'last_name': item.get('lastName', ''),
                                'email': item.get('email', ''),
                                'position': item.get('position', '') or item.get('jobTitle', ''),
                            })

                    new_last_id = body.get('lastId', 0)
                    if not new_last_id or new_last_id == last_id or len(items) < 100:
                        break
                    last_id = new_last_id

                logger.info(
                    f'Snov.io para "{domain}": {len(all_matches)} contactos '
                    f'estratégicos de {total if total > 0 else "N/A"} totales'
                )
                return {
                    'domain': domain,
                    'contacts': all_matches,
                    'total_found': len(all_matches),
                }

        except httpx.HTTPStatusError as e:
            msg = (
                f'Snov.io Domain Search falló para {domain}: '
                f'{e.response.status_code} - {e.response.text[:300]}'
            )
            logger.warning(msg)
            return {'contacts': [], 'error': msg}
        except Exception as e:
            msg = f'Snov.io Domain Search error inesperado para {domain}: {e}'
            logger.warning(msg)
            return {'contacts': [], 'error': msg}

    def enrich_company_contacts(
        self, company_id: str, clean_data: Dict[str, Any]
    ) -> None:
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            logger.error(f'Company {company_id} no encontrada para enriquecer')
            return

        contacts: List[Dict[str, Any]] = clean_data.get('contacts', [])

        has_existing_primary: bool = CompanyContact.objects.filter(
            company=company, is_primary=True
        ).exists()

        created_count: int = 0
        updated_count: int = 0

        for idx, contact_data in enumerate(contacts):
            name: str = (contact_data.get('name') or '').strip()
            if not name:
                continue

            email: str = (contact_data.get('email') or '').strip()
            title: str = (contact_data.get('title') or '').strip()
            phone: str = (contact_data.get('phone') or '').strip()

            defaults: Dict[str, Any] = {
                'name': name,
                'position': title,
                'phone': phone,
                'is_primary': False if has_existing_primary else idx == 0,
            }

            if email:
                defaults['email'] = email
                _, created = CompanyContact.objects.update_or_create(
                    company=company,
                    email=email,
                    defaults=defaults,
                )
            else:
                _, created = CompanyContact.objects.update_or_create(
                    company=company,
                    name=name,
                    defaults=defaults,
                )

            if created:
                created_count += 1
            else:
                updated_count += 1

        logger.info(
            f'CompanyContact enriquecidos para company={company_id}: '
            f'{created_count} creados, {updated_count} actualizados'
        )
