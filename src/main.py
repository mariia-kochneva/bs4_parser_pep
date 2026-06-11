import re
import logging
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, MAIN_DOC_URL, PEP_URL, EXPECTED_STATUS
from outputs import control_output
from utils import get_response, find_tag
from collections import Counter


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        version_link = urljoin(whats_new_url, version_a_tag['href'])
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append(
            (version_link, h1.text, dl_text)
        )

    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = soup.find('div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Не найден список c версиями Python')

    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (link, version, status)
        )

    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_tag = soup.find('div', {'role': 'main'})
    table_tag = main_tag.find('table', {'class': 'docutils'})
    html_a4_tag =table_tag.find('a', {'href': re.compile(r'.+html.*\.zip$')})
    html_a4_link = html_a4_tag['href']
    archive_url = urljoin(downloads_url, html_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    logging.info('Начинаем парсинг PEP')
    response = get_response(session, PEP_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    tables = soup.find_all('table', class_=re.compile('pep-zero-table'))
    if not tables:
        logging.error('Не найдены таблицы со списком PEP')
        return
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
            expected_status_letter = ''
            if len(status_text) > 1:
                expected_status_letter = status_text[1:]
            expected_status = EXPECTED_STATUS.get(
                expected_status_letter, ('Unknown',)
            )[0]
            pep_links.append({
                'number': pep_num,
                'url': pep_url,
                'expected_status': expected_status
            })
    logging.info(f'Найдено {len(pep_links)} PEP для обработки')
    if not pep_links:
        logging.error('Не найдено ни одного PEP')
        return
    status_counter = Counter()
    mismatches = []
    for pep_data in tqdm(pep_links, desc='Обработка PEP'):
        try:
            response_pep = get_response(session, pep_data['url'])
            if response_pep is None:
                status_counter['Ошибка загрузки'] += 1
                continue
            pep_soup = BeautifulSoup(response_pep.text, 'lxml')
            actual_status = 'Unknown'
            for dt in pep_soup.find_all('dt'):
                dt_text = dt.get_text(strip=True)
                if dt_text == 'Status' or dt_text == 'Status:':
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        actual_status = dd.get_text(strip=True)
                        break
            if actual_status == 'Unknown':
                for th in pep_soup.find_all('th'):
                    th_text = th.get_text(strip=True)
                    if th_text == 'Status' or th_text == 'Status:':
                        td = th.find_next_sibling('td')
                        if td:
                            actual_status = td.get_text(strip=True)
                            break
            status_counter[actual_status] += 1
            if actual_status != pep_data['expected_status']:
                mismatches.append({
                    'url': pep_data['url'],
                    'actual': actual_status,
                    'expected': pep_data['expected_status']
                })
        except Exception as e:
            logging.error(f'Ошибка PEP {pep_data["number"]}: {e}')
            status_counter['Error'] += 1
    if mismatches:
        print('\nНесовпадающие статусы:')
        for mismatch in mismatches:
            print(mismatch['url'])
            print(f'Статус в карточке: {mismatch["actual"]}')
            print(f'Ожидаемые статусы: [{mismatch["expected"]}]\n')
    total_count = sum(status_counter.values())
    results = [('Статус', 'Количество')]
    for status, count in sorted(status_counter.items()):
        results.append((status, count))
    results.append(('Total', total_count))

    return results


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')

    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')

    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
