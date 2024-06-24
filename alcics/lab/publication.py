from dataclasses import dataclass, field


score_rosetta = {
    'origin': {'dblp': 1, 'hal': 2},
    'venue': {'CoRR': -1, 'unpublished': -2},
    'type': {'conference': 1, 'journal': 2}
}


@dataclass
class Publication:
    key: str
    title: str
    authors: list
    venue: str
    year: int
    abstract: str = field(repr=False)
    sources: dict = field(repr=False)
    type: str = field(repr=False)

    def __init__(self, raw_list):
        raw_list = sorted(raw_list, key=lambda p: self.score_raw_publi(p), reverse=True)

        for attr in ['key', 'title', 'authors', 'venue', 'year', 'type']:
            setattr(self, attr, raw_list[0][attr])

        self.sources = dict()
        self.abstract = None
        for p in raw_list:
            if self.abstract is None and p.get('abstract'):
                self.abstract = p['abstract']
            origin = p['origin']
            if origin not in self.sources:
                self.sources[origin] = p

    @staticmethod
    def score_raw_publi(paper):
        scores = [v.get(paper[k], 0) for k, v in score_rosetta.items()]
        scores.append(paper['year'])
        return tuple(scores)

    @property
    def string(self):
        return f"{self.title}, by {', '.join(a.name for a in self.authors)}. {self.venue}, {self.year}."
