from dataclasses import dataclass, field
from typing import ClassVar

from alcics.utils.common import LazyRepr
from alcics.utils.logger import logger


@dataclass(repr=False)
class DBAuthor(LazyRepr):
    """
    Blueprint for DB-specific author management.
    """
    db_name: ClassVar[str] = None
    query_id_backoff: ClassVar[float] = 0.0
    query_papers_backoff: ClassVar[float] = 0.0

    name: str
    id: str = None
    aliases: list = field(default_factory=list)

    def query_papers(self, s=None):
        raise NotImplementedError

    def update_values(self, author):
        self.id = author.id
        self.aliases = author.aliases

    def query_id(self, s=None):
        raise NotImplementedError

    def populate_id(self, s=None):
        matches = self.query_id(s)
        size = len(matches)
        if size == 1:
            self.update_values(matches[0])
        elif size > 1:
            choices = '\n'.join(f"{i.url} -> {str(i)}" for i in matches)
            logger.warning(
                f"Multiple entries found for {self.name} in {self.db_name}. "
                f"Please populate manually. "
                f"Entries found:\n{choices}")
        else:
            logger.warning(f"No entry found for {self.name} in {self.db_name}. Please populate manually.")
            logger.warning(self.url)
        return size

    @property
    def url(self):
        raise NotImplementedError

    @property
    def is_set(self):
        return self.id is not None


def clean_aliases(name, alias_list):
    return sorted(set(n for n in alias_list if n != name))

