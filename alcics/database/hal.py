import json
from collections import defaultdict
from dataclasses import dataclass, field

from alcics.database.blueprint import DB, Author
from alcics.utils.common import LazyRepr, unlist
from alcics.utils.requests import autosession, auto_retry_get


@dataclass(repr=False)
class HALAuthor(Author):
    person: int = None
    alt_persons: list = field(default_factory=list)


def parse_facet_author(a):
    """
    Parameters
    ----------
    a: :class:`str`
        Formatted APH author string from HAL API.

    Returns
    -------
    :class:`~alcics.database.hal.HALAuthor`
        Sanitized version.
    """
    name, pid, hid = a.split('_FacetSep_')
    pid = int(pid) if pid and int(pid) else None
    hid = hid if hid else None
    return HALAuthor(names=[name], id=hid, person=pid)


class HAL(DB):
    name = 'hal'
    Author = HALAuthor

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

    @classmethod
    def find_author(cls, q, s=None):
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
        [HALAuthor(id='fabien-mathieu', names=['Fabien Mathieu'])]
        >>> HAL.find_author("Laurent Viennot") # doctest:  +NORMALIZE_WHITESPACE
        [HALAuthor(id='laurentviennot', names=['Laurent Viennot']),
        HALAuthor(names=['Laurent Viennot'], person=1344543)]
        >>> HAL.find_author("NotaSearcherName")
        []
        >>> HAL.find_author("Ana Busic")
        [HALAuthor(id='anabusic', names=['Ana Bušić', 'Bušić Ana'])]
        >>> HAL.find_author("Diego Perino") # doctest:  +NORMALIZE_WHITESPACE
        [HALAuthor(names=['Diego Perino'], person=847558),
        HALAuthor(names=['Diego Perino'], person=978810)]
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
        return [cls.Author(id=k, names=sorted(v)) for k, v in hids.items()] + \
            [cls.Author(person=k, names=sorted(v)) for k, v in pids.items()]

    @classmethod
    def find_papers(cls, a, s=None):
        """

        Parameters
        ----------
        a: :class:`~alcics.database_test.HALAuthor`
            HAL author.
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`list`
            Papers available in DBLP

        Examples
        --------

        >>> papers = sorted(HAL.find_papers(HALAuthor(id='fabien-mathieu')),
        ...                 key=lambda p: p['title'])
        >>> papers[2] # doctest:  +NORMALIZE_WHITESPACE
        {'title': 'Achievable Catalog Size in Peer-to-Peer Video-on-Demand Systems',
        'abstract': 'We analyze a system where $n$ set-top boxes with same upload and storage capacities collaborate to
        serve $r$ videos simultaneously (a typical value is $r=n$). We give upper and lower bounds on the catalog size
        of the system, i.e. the maximal number of distinct videos that can be stored in such a system so that any demand
        of at most $r$ videos can be served. Besides $r/n$, the catalog size is constrained by the storage capacity, the
        upload capacity, and the maximum number of simultaneous connections a box can open. We show that the achievable
        catalog size drastically increases when the upload capacity of the boxes becomes strictly greater than the
        playback rate of videos.', 'key': '471724',
        'conference': 'Proceedings of the 7th Internnational Workshop on Peer-to-Peer Systems (IPTPS)',
        'type': 'COMM', 'year': 2008, 'url': 'https://inria.hal.science/inria-00471724',
        'authors': [HALAuthor(id='yacine-boufkhad', names=['Yacine Boufkhad'], person=7352),
        HALAuthor(id='fabien-mathieu', names=['Fabien Mathieu'], person=446),
        HALAuthor(names=['Fabien de Montgolfier'], person=949013), HALAuthor(names=['Diego Perino']),
        HALAuthor(id='laurentviennot', names=['Laurent Viennot'], person=1841)],
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
        'authors': [HALAuthor(id='fabien-mathieu', names=['Fabien Mathieu'], person=446)],
        'venue': "SSS'07 - 9th international conference on Stabilization, Safety,
        and Security of Distributed Systems"}

        Case of someone with multiple ids one want to cumulate:

        >>> emilio = HAL.find_author('Emilio Calvanese')
        >>> emilio # doctest: +NORMALIZE_WHITESPACE
        [HALAuthor(names=['Emilio Calvanese Strinati'], person=911234),
        HALAuthor(names=['Emilio Calvanese Strinati'], person=1301052)]
        >>> len(HAL.find_papers(emilio[0]))
        9
        >>> len(HAL.find_papers(emilio[1]))
        3
        >>> len(HAL.find_papers(HALAuthor(person=911234, alt_persons=[1301052])))
        12

        Note: an error is raised if not enough data is provided

        >>> HAL.find_papers(HALAuthor())
        Traceback (most recent call last):
        ...
        ValueError: HALAuthor(): must have id or person for papers to be fetched.
        """
        s = autosession(s)
        api = "https://api.archives-ouvertes.fr/search/"
        fields = ['docid', 'abstract_s', 'label_s', 'uri_s', '*Title_s', 'title_s',
                  'producedDateY_i', 'auth_s', 'authFullNamePersonIDIDHal_fs', 'docType_s']
        params = {'fl': fields, 'rows': 2000, 'wt': 'json'}
        if a.id:
            params['q'] = f"authIdHal_s:{a.id}"
        elif a.person:
            params['q'] = f"authIdPerson_i:{a.person}"
        else:
            raise ValueError(f"{a}: must have id or person for papers to be fetched.")
        r = auto_retry_get(s, api, params=params)
        response = json.loads(r.text)['response']
        res = [cls.parse_entry(r) for r in response.get('docs', [])]
        for alt in a.alt_persons:
            res += cls.find_papers(cls.Author(person=alt))
        return res
