import requests
import logging
import json
from dataclasses import dataclass, field
from collections import defaultdict
from bs4 import BeautifulSoup as Soup
from time import sleep


logger = logging.getLogger()


def autosession(s):
    """

    Parameters
    ----------
    s: :class:`~requests.Session`, optional
        A session (may be None).

    Returns
    -------
    :class:`~requests.Session`
        A session.
    """
    if s is None:
        s = requests.Session()
    return s


def auto_retry_get(s, url, params=None):
    """
    Parameters
    ----------
    s: :class:`~requests.Session`
        HTTP session.
    url: :class:`str`
        Entry point to fetch.
    params: :class:`dict`, optional
        Get arguments (appended to URL).

    Returns
    -------
    :class:`~requests.models.Response`
        Result.
    """
    while True:
        r = s.get(url, params=params)
        if r.status_code == 429:
            try:
                t = int(r.headers['Retry-After'])
            except KeyError:
                t = 60
            logger.warning(f'Too many requests. Auto-retry in {t} seconds.')
            sleep(t)
        else:
            return r


class LazyRepr:
    def __repr__(self):
        kws = [f"{key}={value!r}" for key, value in self.__dict__.items() if value]
        return f"{type(self).__name__}({', '.join(kws)})"


class DB:
    """
    Blueprint for DB access
    """
    name = None

    @staticmethod
    def find_author(q, s=None):
        raise NotImplementedError

    @staticmethod
    def find_papers(key, s=None):
        raise NotImplementedError


@dataclass(repr=False)
class DBLPAuthor(LazyRepr):
    dblp_id: str
    dblp_names: list = field(default_factory=list)


class DBLP(DB):
    name = 'dblp'

    @staticmethod
    def parse_entry(r):
        """
        Parameters
        ----------
        r: :class:`~bs4.BeautifulSoup`
            Soup of a result (paper).

        Returns
        -------
        :class:`dict`
            The paper as a dictionary.
        """
        p = r.find()
        res = {'type': p.name,
               'key': p['key']}
        keys = ['title', 'booktitle', 'pages', 'journal', 'year', 'volume', 'number']
        for tag in keys:
            t = p.find(tag)
            if t:
                try:
                    res[tag] = int(t.text)
                except ValueError:
                    res[tag] = t.text
        for tag in ['booktitle', 'journal']:
            t = p.find(tag)
            if t:
                res['venue'] = t.text
        res['authors'] = [DBLPAuthor(dblp_id=a['pid'], dblp_names=[a.text])
                          for a in p('author')]
        return res

    @staticmethod
    def find_author(q, s=None):
        """
        Parameters
        ----------
        q: :class:`str`
            Name of the searcher.
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`list`
            Potential matches.

        Examples
        --------

        >>> DBLP.find_author("Fabien Mathieu")
        [DBLPAuthor(dblp_id='66/2077', dblp_names=['Fabien Mathieu'])]
        >>> sleep(2)
        >>> DBLP.find_author("Manuel Barragan") # doctest:  +NORMALIZE_WHITESPACE
        [DBLPAuthor(dblp_id='07/10587',
        dblp_names=['José M. Peña 0003', 'José Manuel Peña 0002', 'José Manuel Peñá-Barragán']),
        DBLPAuthor(dblp_id='83/3865',
        dblp_names=['Manuel J. Barragan Asian', 'Manuel J. Barragán']),
        DBLPAuthor(dblp_id='188/0198',
        dblp_names=['Manuel Barragán-Villarejo'])]
        >>> sleep(2)
        >>> DBLP.find_author("NotaSearcherName")
        []
        """
        s = autosession(s)
        dblp_api = "https://dblp.org/search/author/api"
        dblp_args = {'q': q}
        r = auto_retry_get(s, dblp_api, params=dblp_args)
        soup = Soup(r.text, features='xml')
        return [DBLPAuthor(dblp_id=hit.url.text.split('pid/')[1],
                           dblp_names=[hit.author.text]+[alia.text for alia in hit('alias')])
                for hit in soup('hit')]

    @staticmethod
    def find_papers(author, s=None):
        """

        Parameters
        ----------
        author: :class:`~alcics.database.DBLPAuthor`
            DBLP author.
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`list`
            Papers available in DBLP

        Examples
        --------

        >>> papers = sorted(DBLP.find_papers(DBLPAuthor(dblp_id='66/2077', dblp_names=['Fabien Mathieu'])),
        ...                 key=lambda p: p['title'])
        >>> papers[0] # doctest:  +NORMALIZE_WHITESPACE
        {'type': 'inproceedings', 'key': 'conf/iptps/BoufkhadMMPV08',
        'title': 'Achievable catalog size in peer-to-peer video-on-demand systems.',
        'booktitle': 'IPTPS', 'pages': 4, 'year': 2008, 'venue': 'IPTPS',
        'authors': [DBLPAuthor(dblp_id='75/5742', dblp_names=['Yacine Boufkhad']),
        DBLPAuthor(dblp_id='66/2077', dblp_names=['Fabien Mathieu']),
        DBLPAuthor(dblp_id='57/6313', dblp_names=['Fabien de Montgolfier']),
        DBLPAuthor(dblp_id='03/3645', dblp_names=['Diego Perino']),
        DBLPAuthor(dblp_id='v/LaurentViennot', dblp_names=['Laurent Viennot'])]}
        >>> papers[-1] # doctest:  +NORMALIZE_WHITESPACE
        {'type': 'inproceedings', 'key': 'conf/sss/Mathieu07',
        'title': 'Upper Bounds for Stabilization in Acyclic Preference-Based Systems.',
        'booktitle': 'SSS', 'pages': '372-382', 'year': 2007, 'venue': 'SSS',
        'authors': [DBLPAuthor(dblp_id='66/2077', dblp_names=['Fabien Mathieu'])]}
        """
        s = autosession(s)
        r = auto_retry_get(s, f'https://dblp.org/pid/{author.dblp_id}.xml')
        soup = Soup(r.text, features='xml')
        return [DBLP.parse_entry(r) for r in soup('r')]


@dataclass(repr=False)
class HALAuthor(LazyRepr):
    hal_id: str = None
    hal_person: int = None
    hal_names: list = field(default_factory=list)
    hal_alt_persons: list = field(default_factory=list)


def parse_facet_author(a):
    """
    Parameters
    ----------
    a: :class:`str`
        Formatted APH author string from HAL API.

    Returns
    -------
    :class:`~alcics.database.HALAuthor`
        Sanitized version.
    """
    name, pid, hid = a.split('_FacetSep_')
    pid = int(pid) if pid and int(pid) else None
    hid = hid if hid else None
    return HALAuthor(hal_names=[name], hal_id=hid, hal_person=pid)


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


class HAL(DB):
    name = 'hal'

    @staticmethod
    def parse_entry(r):
        """
        Parameters
        ----------
        r: :class:`dict`
            Raw dict of a result (paper).

        Returns
        -------
        :class:`dict`
            The paper as a sanitized dictionary.
        """
        rosetta = {'title_s': 'title', 'abstract_s': 'abstract', 'docid': 'key',
                   'bookTitle_s': 'booktitle', 'conferenceTitle_s': 'conference', 'journalTitle_s': 'journal',
                   'docType_s': 'type', 'producedDateY_i': 'year', 'uri_s': 'url'}
        res = {v: unlist(r[k]) for k, v in rosetta.items() if k in r}
        res['authors'] = [parse_facet_author(a) for a in r.get('authFullNamePersonIDIDHal_fs', [])]
        for tag in ['booktitle', 'journal', 'conference']:
            if tag in res:
                res['venue'] = res[tag]
                break
        return res

    @staticmethod
    def find_author(q, s=None):
        """
        Parameters
        ----------
        q: :class:`str`
            Name of the searcher.
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`list`
            Potential matches.

        Examples
        --------

        >>> HAL.find_author("Fabien Mathieu")
        [HALAuthor(hal_id='fabien-mathieu', hal_names=['Fabien Mathieu'])]
        >>> HAL.find_author("Laurent Viennot") # doctest:  +NORMALIZE_WHITESPACE
        [HALAuthor(hal_id='laurentviennot', hal_names=['Laurent Viennot']),
        HALAuthor(hal_person=1344543, hal_names=['Laurent Viennot'])]
        >>> HAL.find_author("NotaSearcherName")
        []
        >>> HAL.find_author("Ana Busic")
        [HALAuthor(hal_id='anabusic', hal_names=['Ana Bušić', 'Bušić Ana'])]
        >>> HAL.find_author("Diego Perino") # doctest:  +NORMALIZE_WHITESPACE
        [HALAuthor(hal_person=847558, hal_names=['Diego Perino']),
        HALAuthor(hal_person=978810, hal_names=['Diego Perino'])]
        """
        s = autosession(s)
        hal_api = "https://api.archives-ouvertes.fr/ref/author/"
        fields = ",".join(['label_s', 'idHal_s', 'person_i'])
        hal_args = {'q': q, 'fl': fields, 'wt': 'json'}
        r = auto_retry_get(s, hal_api, params=hal_args)
        response = json.loads(r.text)['response']
        hids = defaultdict(set)
        pids = defaultdict(set)
        for a in response.get('docs', []):
            if 'label_s' in a:
                if 'idHal_s' in a:
                    hids[a['idHal_s']].add(a.get('label_s'))
                elif 'person_i' in a:
                    pids[a['person_i']].add(a.get('label_s'))
        return [HALAuthor(hal_id=k, hal_names=sorted(v)) for k, v in hids.items()] + \
            [HALAuthor(hal_person=k, hal_names=sorted(v)) for k, v in pids.items()]

    @staticmethod
    def find_papers(a, s=None):
        """

        Parameters
        ----------
        a: :class:`~alcics.database.HALAuthor`
            HAL author.
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`list`
            Papers available in DBLP

        Examples
        --------

        >>> papers = sorted(HAL.find_papers(HALAuthor(hal_id='fabien-mathieu')),
        ...                 key=lambda p: p['title'])
        >>> papers[2] # doctest:  +NORMALIZE_WHITESPACE
        {'title': 'Achievable Catalog Size in Peer-to-Peer Video-on-Demand Systems',
        'abstract': 'We analyze a system where $n$ set-top boxes with same upload and storage capacities collaborate to
        serve $r$ videos simultaneously (a typical value is $r=n$). We give upper and lower bounds on the catalog size
        of the system, i.e. the maximal number of distinct videos that can be stored in such a system so that any
        demand of at most $r$ videos can be served. Besides $r/n$, the catalog size is constrained by the storage
        capacity, the upload capacity, and the maximum number of simultaneous connections a box can open. We show that
        the achievable catalog size drastically increases when the upload capacity of the boxes becomes strictly greater
        than the playback rate of videos.', 'key': '471724',
        'conference': 'Proceedings of the 7th Internnational Workshop on Peer-to-Peer Systems (IPTPS)',
        'type': 'COMM', 'year': 2008, 'url': 'https://inria.hal.science/inria-00471724',
        'authors': [HALAuthor(hal_id='yacine-boufkhad', hal_person=7352, hal_names=['Yacine Boufkhad']),
        HALAuthor(hal_id='fabien-mathieu', hal_person=446, hal_names=['Fabien Mathieu']),
        HALAuthor(hal_person=949013, hal_names=['Fabien de Montgolfier']),
        HALAuthor(hal_names=['Diego Perino']),
        HALAuthor(hal_id='laurentviennot', hal_person=1841, hal_names=['Laurent Viennot'])],
        'venue': 'Proceedings of the 7th Internnational Workshop on Peer-to-Peer Systems (IPTPS)'}
        >>> papers[-7] # doctest:  +NORMALIZE_WHITESPACE
        {'title': 'Upper bounds for stabilization in acyclic preference-based systems',
        'abstract': 'Preference-based systems (p.b.s.) describe interactions between nodes of a system that can rank
        their neighbors. Previous work has shown that p.b.s. converge to a unique locally stable matching if an
        acyclicity property is verified. In the following we analyze acyclic p.b.s. with respect to the
        self-stabilization theory. We prove that the round complexity is bounded by n/2 for the adversarial daemon.
        The step complexity is equivalent to (n^2)/4 for the round robin daemon, and exponential for the general
        adversarial daemon.', 'key': '668356',
        'conference': "SSS'07 - 9th international conference on Stabilization, Safety,
        and Security of Distributed Systems",
        'type': 'COMM', 'year': 2007, 'url': 'https://inria.hal.science/hal-00668356',
        'authors': [HALAuthor(hal_id='fabien-mathieu', hal_person=446, hal_names=['Fabien Mathieu'])],
        'venue': "SSS'07 - 9th international conference on Stabilization, Safety,
        and Security of Distributed Systems"}

        Case of someone with multiple ids one want to cumulate:

        >>> emilio = HAL.find_author('Emilio Calvanese')
        >>> emilio # doctest: +NORMALIZE_WHITESPACE
        [HALAuthor(hal_person=911234, hal_names=['Emilio Calvanese Strinati']),
        HALAuthor(hal_person=1301052, hal_names=['Emilio Calvanese Strinati'])]
        >>> len(HAL.find_papers(emilio[0]))
        9
        >>> len(HAL.find_papers(emilio[1]))
        3
        >>> len(HAL.find_papers(HALAuthor(hal_person=911234, hal_alt_persons=[1301052])))
        12

        Note: an error is raised if not enough data is provided

        >>> HAL.find_papers(HALAuthor())
        Traceback (most recent call last):
        ...
        ValueError: HALAuthor(): must have hal_id or hal_person for papers to be fetched.
        """
        s = autosession(s)
        api = "https://api.archives-ouvertes.fr/search/"
        fields = ['docid', 'abstract_s', 'label_s', 'uri_s', '*Title_s', 'title_s',
                  'producedDateY_i', 'auth_s', 'authFullNamePersonIDIDHal_fs', 'docType_s']
        params = {'fl': fields, 'rows': 2000, 'wt': 'json'}
        if a.hal_id:
            params['q'] = f"authIdHal_s:{a.hal_id}"
        elif a.hal_person:
            params['q'] = f"authIdPerson_i:{a.hal_person}"
        else:
            raise ValueError(f"{a}: must have hal_id or hal_person for papers to be fetched.")
        r = auto_retry_get(s, api, params=params)
        response = json.loads(r.text)['response']
        res = [HAL.parse_entry(r) for r in response.get('docs', [])]
        for alt in a.hal_alt_persons:
            res += HAL.find_papers(HALAuthor(hal_person=alt))
        return res
