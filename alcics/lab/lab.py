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


class Lab(MixInIO):
    """
    Parameters
    ----------
    members: :class:`list` of `str`
        Names of the lab members.
    db_dict: :class:`dict`
        Publication DBs to use. Default to all available.
    """
    constructor = Member
    """Class attribute: constructor for members of the lab."""

    def __init__(self, members, db_dict=None):
        self.members = dict()
        self.member_keys = None
        if db_dict is None:
            db_dict = get_classes(DBAuthor, key='db_name')
        for name in members:
            member = self.constructor(name, db_dict=db_dict)
            self.members[member.key] = member
        self.publications = None
        self.s = autosession(None)

    @property
    def member_list(self):
        """
        :class:`list`
            List of lab members.
        """
        return [m for m in self.members.values()]

    def manual_update(self, up_list):
        """
        Inject some populated DBAuthors in the lab.

        Parameters
        ----------
        up_list: :class:`list` of :class:`~alcics.database.blueprint.DBAuthor`
            Info to inject.

        Returns
        -------
        None
        """
        for db_auth in up_list:
            name = db_auth.name
            if name not in self.members:
                logger.warning(f"{name} is not a registered team author.")
                continue
            member = self.members[name]
            db = db_auth.db_name
            member.sources[db].update_values(db_auth)

    def get_ids(self, rewrite=False):
        """
        Get DB identifiers.

        Parameters
        ----------
        rewrite: :class:`bool`, default=False
            Update even if identifiers are already set.

        Returns
        -------
        None
        """
        for member in self.members.values():
            member.prepare(s=self.s, backoff=True, rewrite=rewrite)

    def compute_keys(self):
        """
        Makes a key dictionary so that any name, alias, or db identifier of a member can be linked to her key.

        Returns
        -------
        None
        """
        self.member_keys = dict()
        for member in self.members.values():
            target = member.key
            for db_author in member.sources.values():
                for key in db_author.iter_keys():
                    self.member_keys[key] = target

    def get_publications(self):
        """
        * Retrieve all publications from members in their databases
        * Remove full duplicates
        * Gather pseudo-duplicates and populate publications
        * Populate each member's publication list with her publications' keys.

        Returns
        -------
        None
        """
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
        """
        Simple texter that gives title and abstract (if any) from a publication key.

        Parameters
        ----------
        key: :class:`str`
            Identifier of a publication.

        Returns
        -------
        :class:`str`
            Publication description.
        """
        paper = self.publications[key]
        res = paper.title
        if paper.abstract:
            res = f"{res}\n{paper.abstract}"
        return res

    def member_to_text(self, key):
        """
        Simple texter that concatenates all publications of a member (titles and possibly abstracts).

        Parameters
        ----------
        key: :class:`str`
            Identifier of a member.

        Returns
        -------
        :class:`str`
            Member description.
        """
        member = self.members[self.member_keys[key]]
        return "\n".join(self.publi_to_text(k) for k in member.publications)
