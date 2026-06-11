import logging
import re
from urllib.parse import urljoin

from constants import PEP_URL, EXPECTED_STATUS
from exceptions import ParserFindTagException
from requests import RequestException


def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        response.raise_for_status()
        return response
    except RequestException as e:
        logging.error(f'Возникла ошибка при загрузке страницы {url}: {e}')
        return None


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg)
        raise ParserFindTagException(error_msg)
    return searched_tag


def collect_pep_links(soup):
    tables = soup.find_all('table', class_=re.compile('pep-zero-table'))
    pep_links = []
    seen_numbers = set()
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            number_cell = cells[1]
            link = number_cell.find('a')
            if not link:
                continue
            href = link.get('href', '')
            if not href:
                continue
            pep_num = link.get_text(strip=True)
            if not pep_num.isdigit() or pep_num == '0':
                continue
            if pep_num in seen_numbers:
                continue
            seen_numbers.add(pep_num)
            pep_url = urljoin(PEP_URL, href)
            status_cell = cells[0]
            status_text = status_cell.get_text(strip=True)
            expected_status_letter = status_text[1:] if len(status_text) > 1 else ''
            expected_status = EXPECTED_STATUS.get(expected_status_letter, ('Unknown',))[0]
            pep_links.append({
                'number': pep_num,
                'url': pep_url,
                'expected_status': expected_status
            })
    return pep_links


def get_actual_status(pep_soup):
    for dt in pep_soup.find_all('dt'):
        dt_text = dt.get_text(strip=True)
        if dt_text == 'Status' or dt_text == 'Status:':
            dd = dt.find_next_sibling('dd')
            if dd:
                return dd.get_text(strip=True)
    for th in pep_soup.find_all('th'):
        th_text = th.get_text(strip=True)
        if th_text == 'Status' or th_text == 'Status:':
            td = th.find_next_sibling('td')
            if td:
                return td.get_text(strip=True)
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
