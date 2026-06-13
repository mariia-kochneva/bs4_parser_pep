import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from constants import PEP_URL, EXPECTED_STATUS
from exceptions import ParserFindTagException, ParserHTTPError


def get_response(session, url, encoding='utf-8'):
    response = session.get(url)
    response.encoding = encoding
    response.raise_for_status()
    return response


def get_soup(session, url, encoding='utf-8'):
    response = get_response(session, url, encoding)
    return BeautifulSoup(response.text, 'lxml')


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        raise ParserFindTagException(f'Не найден тег {tag} {attrs}')
    return searched_tag


def collect_pep_links(soup):
    pep_links = []
    seen_numbers = set()
    for link in soup.select('table.pep-zero-table td:nth-child(2) a'):
        pep_num = link.get_text(strip=True)
        if not pep_num.isdigit() or pep_num == '0' or pep_num in seen_numbers:
            continue
        seen_numbers.add(pep_num)
        pep_url = urljoin(PEP_URL, link['href'])
        status_cell = link.find_parent('td').find_previous_sibling('td')
        status_text = status_cell.get_text(strip=True) if status_cell else ''
        status_letter = status_text[1] if len(status_text) > 1 else ''
        expected_status = EXPECTED_STATUS.get(status_letter, ('Unknown',))[0]
        pep_links.append({
            'number': pep_num,
            'url': pep_url,
            'expected_status': expected_status
        })
    return pep_links


def get_actual_status(pep_soup):
    for tag in pep_soup.find_all(['dt', 'th']):
        text = tag.get_text(strip=True).lower()
        if 'status' in text:
            next_elem = tag.find_next_sibling(['dd', 'td'])
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
