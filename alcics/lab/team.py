from dataclasses import dataclass, field, asdict
from time import sleep

from alcics.utils.common import LazyRepr, get_classes
from alcics.utils.logger import logger
from alcics.utils.mixinio import MixInIO
from alcics.utils.requests import autosession
from alcics.database.blueprint import DBAuthor


class Member(LazyRepr):

    def __init__(self, name, db_dict=None):
        self.name = name
        if db_dict is None:
            db_dict = get_classes(DBAuthor, key='db_name')
        dbs = [db for db in db_dict.keys()]
        self.sources = {db: db_dict[db](name=name) for db in dbs}
        self.papers = []

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
                papers += db_author.query_papers(s)
                if backoff:
                    sleep(db_author.query_papers_backoff)
            else:
                logger.warning(f"{db_author.name} is not properly identified in {db_author.db_name}.")
        return papers


class Team(MixInIO):
    Member = Member

    def __init__(self, members):
        self.members = None
        self.member_dict = None
        self.initiate_members(members)
        self.articles = None
        self.s = autosession(None)

    def initiate_members(self, members, db_dict=None):
        if db_dict is None:
            db_dict = get_classes(DBAuthor, key='db_name')
        self.members = [Member(name, db_dict=db_dict) for name in members]
        self.member_dict = {m.name: m for m in self.members}

    def manual_update(self, up_list):
        for db_auth in up_list:
            name = db_auth.name
            if name not in self.member_dict:
                logger.warning(f"{name} is not a registered team author.")
                continue
            member = self.member_dict[name]
            db = db_auth.db_name
            member.sources[db].update_values(db_auth)

    def get_ids(self, rewrite=False):
        for member in self.members:
            member.prepare(s=self.s, backoff=True, rewrite=rewrite)
