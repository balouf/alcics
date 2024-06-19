from dataclasses import dataclass, field, asdict
from time import sleep

from alcics.utils.common import LazyRepr, get_classes
from alcics.utils.logger import logger
from alcics.utils.mixinio import MixInIO
from alcics.utils.requests import autosession
from alcics.database.blueprint import DB
from alcics.database.hal import HALAuthor
from alcics.database.dblp import DBLPAuthor


@dataclass(repr=False)
class Member(LazyRepr):
    name: str
    hal: HALAuthor = None
    dblp: DBLPAuthor = None
    papers: list = field(default_factory=list)


class Team(MixInIO):
    Member = Member

    def __init__(self, members):
        self.members = None
        self.member_dict = None
        self.initiate_members(members)
        self.articles = None

    def initiate_members(self, members):
        self.members = [Member(name) for name in members]
        self.member_dict = {m.name: m for m in self.members}

    def set_db_id(self, name, db, db_id, rewrite=False):
        if name not in self.member_dict:
            logger.warning(f"{name} is not a registered team author.")
            return False
        member = self.member_dict[name]
        if db not in asdict(member):
            logger.warning(f"{db} is not a valid attribute for {name}.")
            return False
        if getattr(member, db) is not None and not rewrite:
            logger.warning(f"{name} has a populated {db} attribute. Skip.")
            return False
        setattr(member, db, db_id)
        return True

    def get_ids(self, dbs=None, manual_input=None, rewrite=False):
        s = autosession(None)
        if dbs is None:
            dbs = get_classes(DB)

        if manual_input is not None:
            for db, entries in manual_input.items():
                for name, aut_id in entries.items():
                    self.set_db_id(name, db, aut_id, rewrite=rewrite)

        for name, member in self.member_dict.items():
            for db_name, v in asdict(member).items():
                if db_name in dbs and v is None:
                    db = dbs[db_name]
                    id_list = db.find_author(name, s=s)
                    if len(id_list) == 1:
                        self.set_db_id(name, db_name, id_list[0], rewrite=rewrite)
                    elif len(id_list) == 0:
                        logger.warning(f"No entry found for {name} in {db_name}. Please populate manually.")
                    else:
                        choices = '\n'.join(str(i) for i in id_list)
                        logger.warning(
                            f"Multiple entries found for {name} in {db_name}. "
                            f"Please populate manually. "
                            f"Entries found:\n{choices}")
                    sleep(db.author_backoff)
