class LazyRepr:
    """
    MixIn that hides empty fields in dataclasses repr's.
    """
    def __repr__(self):
        kws = [f"{key}={value!r}" for key, value in self.__dict__.items() if value]
        return f"{type(self).__name__}({', '.join(kws)})"


def unlist(x):
    """
    Parameters
    ----------
    x: :class:`str` or :class:`list` or :class:`int`
        Something.

    Returns
    -------
    x: :class:`str` or :class:`int`
        If it's a list, make it flat.
    """
    return " ".join(x) if isinstance(x, list) else x


def get_classes(root, key='name'):
    """
    Parameters
    ----------
    root: :class:`class`
        Starting class (can be abstract).
    key: :class:`str`, default='name'
        Attribute to look-up

    Returns
    -------
    :class:`dict`
        Dictionaries of all subclasses that have a key attribute (as in class attribute `key`).

    Examples
    --------

    >>> from alcics.database.blueprint import DB
    >>> subclasses = get_classes(DB)
    >>> dict(sorted(subclasses.items())) # doctest: +NORMALIZE_WHITESPACE
    {'dblp': <class 'alcics.database.dblp.DBLP'>,
    'hal': <class 'alcics.database.hal.HAL'>}
    """
    result = {getattr(c, key): c for c in root.__subclasses__() if getattr(c, key)}
    for c in root.__subclasses__():
        result.update(get_classes(c))
    return result