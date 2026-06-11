class ParserFindTagException(Exception):
    """Вызывается, когда парсер не может найти тег."""
    pass


class ParserNotFoundVersionException(Exception):
    """Вызывается, когда не найден список версий Python."""
    pass
