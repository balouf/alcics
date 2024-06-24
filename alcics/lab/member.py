from time import sleep

from alcics.database.blueprint import DBAuthor
from alcics.utils.common import LazyRepr, get_classes
from alcics.utils.logger import logger


class Member(LazyRepr):

    def __init__(self, name, pid=None, db_dict=None):
        self.name = name
        self.pid = pid
        if db_dict is None:
            db_dict = get_classes(DBAuthor, key='db_name')
        self.sources = {db: author(name=name) for db, author in db_dict.items()}
        self.publications = []

    @property
    def key(self):
        return self.pid if self.pid else self.name

    def prepare(self, s=None, backoff=False, rewrite=False):
        for db_author in self.sources.values():
            if rewrite or not db_author.is_set:
                db_author.populate_id(s)
                if backoff:
                    sleep(db_author.query_id_backoff)

    def get_papers(self, s=None, backoff=False):
        papers = []
        for db_author in self.sources.values():
            if db_author.is_set:
                papers += db_author.query_publications(s)
                if backoff:
                    sleep(db_author.query_publications_backoff)
            else:
                logger.warning(f"{db_author.name} is not properly identified in {db_author.db_name}.")
        return papers
