from pathlib import Path

MAIN_DOC_URL = 'https://docs.python.org/3/'
PEP_URL = 'https://peps.python.org/'
BASE_DIR = Path(__file__).parent

# Форматы даты и времени
FILE_DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'

# Настройки логирования
LOG_FORMAT = '"%(asctime)s - [%(levelname)s] - %(message)s"'
LOG_DIR = 'logs'
LOG_FILE = 'parser.log'
LOG_DATE_FORMAT = '%d.%m.%Y %H:%M:%S'

# Режимы вывода
PRETTY_OUTPUT = 'pretty'
FILE_OUTPUT = 'file'

# Директории
RESULTS_DIR = 'results'
DOWNLOADS_DIR = 'downloads'

EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}
