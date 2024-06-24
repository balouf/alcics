from bof.fuzz import Process
from collections import defaultdict
import numpy as np

from alcics.lab.member import Member
from alcics.lab.publication import Publication
from alcics.utils.common import get_classes
from alcics.utils.logger import logger
from alcics.utils.mixinio import MixInIO
from alcics.utils.requests import autosession
from alcics.database.blueprint import DBAuthor


class Team(MixInIO):
    Member = Member

    def __init__(self, members, db_dict=None):
        self.members = dict()
        self.member_keys = None
        if db_dict is None:
            db_dict = get_classes(DBAuthor, key='db_name')
        for name in members:
            member = Member(name, db_dict=db_dict)
            self.members[member.key] = member
        self.publications = None
        self.s = autosession(None)

    @property
    def member_list(self):
        return [m for m in self.members.values()]

    def manual_update(self, up_list):
        for db_auth in up_list:
            name = db_auth.name
            if name not in self.members:
                logger.warning(f"{name} is not a registered team author.")
                continue
            member = self.members[name]
            db = db_auth.db_name
            member.sources[db].update_values(db_auth)

    def get_ids(self, rewrite=False):
        for member in self.members.values():
            member.prepare(s=self.s, backoff=True, rewrite=rewrite)

    def compute_keys(self):
        self.member_keys = dict()
        for member in self.members.values():
            target = member.key
            for db_author in member.sources.values():
                for key in db_author.iter_keys():
                    self.member_keys[key] = target

    def get_publications(self):
        self.publications = dict()
        self.compute_keys()
        raw = []
        for member in self.members.values():
            raw += member.get_papers(s=self.s, backoff=True)

        raw = [p for p in {a['key']: a for a in raw}.values()]

        p = Process(length_impact=.2)
        p.fit([p['title'] for p in raw])

        done = np.zeros(len(raw), dtype=bool)
        for i, paper in enumerate(raw):
            if done[i]:
                continue
            locs = np.where(p.transform([paper['title']], threshold=.9)[0, :] > 9)[0]
            article = Publication([raw[i] for i in locs])
            self.publications[article.key] = article
            done[locs] = True

        aut2pap = defaultdict(set)
        for k, paper in self.publications.items():
            for a in paper.authors:
                for author_id in a.iter_keys():
                    if author_id in self.member_keys:
                        aut2pap[self.member_keys[author_id]].add(k)

        for author, papers in aut2pap.items():
            self.members[author].publications = list(papers)

    def publi_to_text(self, key):
        paper = self.publications[key]
        res = paper.title
        if paper.abstract:
            res = f"{res}\n{paper.abstract}"
        return res

    def member_to_text(self, key):
        member = self.members[self.member_keys[key]]
        return "\n".join(self.publi_to_text(k) for k in member.publications)
