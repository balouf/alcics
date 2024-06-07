import requests
from dataclasses import dataclass
from bs4 import BeautifulSoup as Soup
from time import sleep


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


@dataclass
class DBLPAuthor:
    dblp_id: str
    dblp_name: str


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
        res['authors'] = [DBLPAuthor(dblp_id=a['pid'], dblp_name=a.text) for a in p('author')]
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
        [DBLPAuthor(dblp_id='66/2077', dblp_name='Fabien Mathieu')]
        >>> sleep(2)
        >>> DBLP.find_author("Viennot") # doctest:  +NORMALIZE_WHITESPACE
        [DBLPAuthor(dblp_id='179/7690', dblp_name='David Viennot'),
        DBLPAuthor(dblp_id='02/3766', dblp_name='Gérard Viennot'),
        DBLPAuthor(dblp_id='v/LaurentViennot', dblp_name='Laurent Viennot'),
        DBLPAuthor(dblp_id='276/0712', dblp_name='Mathieu Viennot'),
        DBLPAuthor(dblp_id='05/998', dblp_name='Nicolas Viennot'),
        DBLPAuthor(dblp_id='11/8776', dblp_name='Simon Viennot'),
        DBLPAuthor(dblp_id='41/5784', dblp_name='Xavier Gérard Viennot')]
        >>> sleep(2)
        >>> DBLP.find_author("NotaSearcherName")
        []
        """
        s = autosession(s)
        dblp_api = "https://dblp.org/search/author/api"
        dblp_args = {'q': q}
        while True:
            r = s.get(dblp_api, params=dblp_args)
            if r.status_code == 429:
                t = int(r.headers['Retry-After'])
                print(f'Rate-limit: retry in {t} seconds.')
                sleep(t)
            else:
                break
        soup = Soup(r.text, features='xml')
        return [DBLPAuthor(dblp_id=hit.url.text.split('pid/')[1], dblp_name=hit.author.text)
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

        >>> papers = sorted(DBLP.find_papers(DBLPAuthor(dblp_id='66/2077', dblp_name='Fabien Mathieu')),
        ...                 key=lambda p: p['title'])
        >>> papers[0] # doctest:  +NORMALIZE_WHITESPACE
        {'type': 'inproceedings', 'key': 'conf/iptps/BoufkhadMMPV08',
        'title': 'Achievable catalog size in peer-to-peer video-on-demand systems.',
        'booktitle': 'IPTPS', 'pages': 4, 'year': 2008,
        'authors': [DBLPAuthor(dblp_id='75/5742', dblp_name='Yacine Boufkhad'),
        DBLPAuthor(dblp_id='66/2077', dblp_name='Fabien Mathieu'),
        DBLPAuthor(dblp_id='57/6313', dblp_name='Fabien de Montgolfier'),
        DBLPAuthor(dblp_id='03/3645', dblp_name='Diego Perino'),
        DBLPAuthor(dblp_id='v/LaurentViennot', dblp_name='Laurent Viennot')]}
        >>> papers[-1] # doctest:  +NORMALIZE_WHITESPACE
        {'type': 'inproceedings', 'key': 'conf/sss/Mathieu07',
        'title': 'Upper Bounds for Stabilization in Acyclic Preference-Based Systems.',
        'booktitle': 'SSS', 'pages': '372-382', 'year': 2007,
        'authors': [DBLPAuthor(dblp_id='66/2077', dblp_name='Fabien Mathieu')]}
        """
        s = autosession(s)
        r = s.get(f'https://dblp.org/pid/{author.dblp_id}.xml')
        soup = Soup(r.text, features='xml')
        return [DBLP.parse_entry(r) for r in soup('r')]
