import re
import logging
from urllib.parse import urljoin

import requests_cache
from tqdm import tqdm
from collections import Counter

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, MAIN_DOC_URL, PEP_URL
from outputs import control_output
from utils import get_soup, find_tag, collect_pep_links, get_actual_status
from utils import print_mismatches, build_status_table
from exceptions import ParserNotFoundVersionException


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = get_soup(session, whats_new_url)
    if soup is None:
        return
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        version_link = urljoin(whats_new_url, version_a_tag['href'])
        soup = get_soup(session, version_link)
        if soup is None:
            continue
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append(
            (version_link, h1.text, dl_text)
        )

    return results


def latest_versions(session):
    soup = get_soup(session, MAIN_DOC_URL)
    if soup is None:
        return
    sidebar = soup.find('div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    a_tags = None
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    if a_tags is None:
        raise ParserNotFoundVersionException(
            'Не найден список c версиями Python'
        )
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append((link, version, status))

    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = get_soup(session, downloads_url)
    if soup is None:
        return
    main_tag = soup.find('div', {'role': 'main'})
    table_tag = main_tag.find('table', {'class': 'docutils'})
    html_a4_tag = table_tag.find('a', {'href': re.compile(r'.+html.*\.zip$')})
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


def process_pep(pep_data, session):
    pep_soup = get_soup(session, pep_data['url'])
    if pep_soup is None:
        return 'Ошибка загрузки', None
    actual_status = get_actual_status(pep_soup)
    mismatch = None
    if actual_status != pep_data['expected_status']:
        mismatch = {
            'url': pep_data['url'],
            'actual': actual_status,
            'expected': pep_data['expected_status']
        }
    return actual_status, mismatch


def pep(session):
    logging.info('Начинаем парсинг PEP')
    soup = get_soup(session, PEP_URL)
    if soup is None:
        return
    pep_links = collect_pep_links(soup)
    logging.info(f'Найдено {len(pep_links)} PEP для обработки')
    if not pep_links:
        logging.error('Не найдено ни одного PEP')
        return
    status_counter = Counter()
    mismatches = []
    for pep_data in tqdm(pep_links, desc='Обработка PEP'):
        actual_status, mismatch = process_pep(pep_data, session)
        status_counter[actual_status] += 1
        if mismatch:
            mismatches.append(mismatch)
    print_mismatches(mismatches)
    results = build_status_table(status_counter)
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
    try:
        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)
        if results is not None:
            control_output(results, args)
    except Exception as e:
        logging.error(f'Ошибка при выполнении парсера: {e}')
        raise

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
