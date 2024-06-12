from dataclasses import dataclass, field

from alcics.utils.common import LazyRepr


@dataclass(repr=False)
class Author(LazyRepr):
    """
    Blueprint for DB-specific author data.
    """
    id: str = None
    names: list = field(default_factory=list)


class DB:
    """
    Blueprint for DB access.
    """
    name = None
    Author = Author

    author_backoff = 0
    papers_backoff = 0

    @classmethod
    def find_author(cls, q, s=None):
        raise NotImplementedError

    @classmethod
    def find_papers(cls, key, s=None):
        raise NotImplementedError
