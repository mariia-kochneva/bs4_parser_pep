import logging
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from constants import PEP_URL, EXPECTED_STATUS
from exceptions import ParserFindTagException
from requests import RequestException


def get_response(session, url, encoding='utf-8'):
    try:
        response = session.get(url)
        response.encoding = encoding
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logging.error(f'Возникла ошибка при загрузке страницы {url}: {e}')
        return None


def get_soup(session, url, encoding='utf-8'):
    response = get_response(session, url, encoding)
    if response is None:
        return None
    return BeautifulSoup(response.text, 'lxml')


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg)
        raise ParserFindTagException(error_msg)
    return searched_tag


def collect_pep_links(soup):
    pep_links = []
    seen_numbers = set()
    rows = soup.select('table.pep-zero-table tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 2:
            continue
        link = cells[1].find('a')
        if not link:
            continue
        pep_num = link.get_text(strip=True)
        if not pep_num.isdigit() or pep_num == '0' or pep_num in seen_numbers:
            continue
        seen_numbers.add(pep_num)
        pep_url = urljoin(PEP_URL, link.get('href'))
        status_text = cells[0].get_text(strip=True)
        expected_status_letter = (
            status_text[1:] if len(status_text) > 1 else ''
        )
        expected_status = EXPECTED_STATUS.get(
            expected_status_letter, ('Unknown',)
        )[0]
        pep_links.append({
            'number': pep_num,
            'url': pep_url,
            'expected_status': expected_status
        })
    return pep_links


def get_actual_status(pep_soup):
    status_elem = pep_soup.find(
        lambda tag: tag.name in ('dt', 'th') and 
        tag.get_text(strip=True).lower().startswith('status')
    )
    if status_elem:
        next_elem = status_elem.find_next_sibling(['dd', 'td'])
        if next_elem:
            return next_elem.get_text(strip=True)
    return 'Unknown'


def print_mismatches(mismatches):
    if mismatches:
        print('\nНесовпадающие статусы:')
        for mismatch in mismatches:
            print(mismatch['url'])
            print(f'Статус в карточке: {mismatch["actual"]}')
            print(f'Ожидаемые статусы: [{mismatch["expected"]}]\n')


def build_status_table(status_counter):
    total_count = sum(status_counter.values())
    results = [('Статус', 'Количество')]
    for status, count in sorted(status_counter.items()):
        results.append((status, count))
    results.append(('Total', total_count))
    return results
