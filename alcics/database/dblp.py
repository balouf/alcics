from dataclasses import dataclass, field
from time import sleep

from bs4 import BeautifulSoup as Soup

from alcics.database.blueprint import DB, Author
from alcics.utils.requests import autosession, auto_retry_get


@dataclass(repr=False)
class DBLPAuthor(Author):

    @property
    def url(self):
        return f'https://dblp.org/pid/{self.id}.html'


class DBLP(DB):
    name = 'dblp'
    Author = DBLPAuthor

    author_backoff = 7
    papers_backoff = 2

    @classmethod
    def parse_entry(cls, r):
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
        res['authors'] = [cls.Author(id=a['pid'], names=[a.text])
                          for a in p('author')]
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

        >>> DBLP.find_author("Fabien Mathieu")
        [DBLPAuthor(id='66/2077', names=['Fabien Mathieu'])]
        >>> sleep(2)
        >>> DBLP.find_author("Manuel Barragan") # doctest:  +NORMALIZE_WHITESPACE
        [DBLPAuthor(id='07/10587',
        names=['José M. Peña 0003', 'José Manuel Peña 0002', 'José Manuel Peñá-Barragán']),
        DBLPAuthor(id='83/3865',
        names=['Manuel J. Barragan Asian', 'Manuel J. Barragán']),
        DBLPAuthor(id='188/0198',
        names=['Manuel Barragán-Villarejo'])]
        >>> sleep(2)
        >>> DBLP.find_author("NotaSearcherName")
        []
        """
        s = autosession(s)
        dblp_api = "https://dblp.org/search/author/api"
        dblp_args = {'q': q}
        r = auto_retry_get(s, dblp_api, params=dblp_args)
        soup = Soup(r.text, features='xml')
        return [cls.Author(id=hit.url.text.split('pid/')[1],
                           names=[hit.author.text]+[alia.text for alia in hit('alias')])
                for hit in soup('hit')]

    @classmethod
    def find_papers(cls, author, s=None):
        """

        Parameters
        ----------
        author: :class:`~alcics.database.dblp.DBLPAuthor`
            DBLP author.
        s: :class:`~requests.Session`, optional
            Session.

        Returns
        -------
        :class:`list`
            Papers available in DBLP

        Examples
        --------

        >>> papers = sorted(DBLP.find_papers(DBLPAuthor(id='66/2077', names=['Fabien Mathieu'])),
        ...                 key=lambda p: p['title'])
        >>> papers[0] # doctest:  +NORMALIZE_WHITESPACE
        {'type': 'inproceedings', 'key': 'conf/iptps/BoufkhadMMPV08',
        'title': 'Achievable catalog size in peer-to-peer video-on-demand systems.',
        'booktitle': 'IPTPS', 'pages': 4, 'year': 2008, 'venue': 'IPTPS',
        'authors': [DBLPAuthor(id='75/5742', names=['Yacine Boufkhad']),
        DBLPAuthor(id='66/2077', names=['Fabien Mathieu']),
        DBLPAuthor(id='57/6313', names=['Fabien de Montgolfier']),
        DBLPAuthor(id='03/3645', names=['Diego Perino']),
        DBLPAuthor(id='v/LaurentViennot', names=['Laurent Viennot'])]}
        >>> papers[-1] # doctest:  +NORMALIZE_WHITESPACE
        {'type': 'inproceedings', 'key': 'conf/sss/Mathieu07',
        'title': 'Upper Bounds for Stabilization in Acyclic Preference-Based Systems.',
        'booktitle': 'SSS', 'pages': '372-382', 'year': 2007, 'venue': 'SSS',
        'authors': [DBLPAuthor(id='66/2077', names=['Fabien Mathieu'])]}
        """
        s = autosession(s)
        r = auto_retry_get(s, f'https://dblp.org/pid/{author.id}.xml')
        soup = Soup(r.text, features='xml')
        return [cls.parse_entry(r) for r in soup('r')]
