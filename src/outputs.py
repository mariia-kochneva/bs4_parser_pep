import csv
import datetime as dt
import logging

from prettytable import PrettyTable

from constants import (
    BASE_DIR, FILE_DATETIME_FORMAT, PRETTY_OUTPUT, FILE_OUTPUT, RESULTS_DIR
)


def pretty_output(results):
    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    results_dir = BASE_DIR / RESULTS_DIR
    results_dir.mkdir(exist_ok=True)
    parser_mode = cli_args.mode
    now = dt.datetime.now()
    now_formatted = now.strftime(FILE_DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = results_dir / file_name
    with open(file_path, 'w', encoding='utf-8') as f:
        writer = csv.writer(f, dialect='unix')
        writer.writerows(results)
    logging.info(f'Файл с результатами был сохранён: {file_path}')


def default_output(results):
    for row in results:
        print(*row)


def control_output(results, cli_args):
    output = cli_args.output
    if output == PRETTY_OUTPUT:
        pretty_output(results)
    elif output == FILE_OUTPUT:
        file_output(results, cli_args)
    else:
        default_output(results)
