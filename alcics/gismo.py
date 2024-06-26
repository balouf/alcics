from sklearn.feature_extraction.text import CountVectorizer

from gismo.corpus import Corpus
from gismo.embedding import Embedding
from gismo.gismo import Gismo


def make_post_publi(lab):
    def to_bib(g, i):
        item = g.corpus[i]
        return lab.publications[item]
    return to_bib


def make_gismo(lab, vectorizer_parameters=None):
    parameters = {'ngram_range': (1, 3),
                             'dtype': float,
                             'stop_words': sw,
                             'min_df':3}
    if vectorizer_parameters is not None:
        parameters.update(vectorizer_parameters)
    corpus = Corpus([p for p in lab.publications], to_text=lab.publi_to_text)
    vectorizer = CountVectorizer(**parameters)
    embedding = Embedding(vectorizer=vectorizer)
    embedding.fit_transform(corpus)
    gismo = Gismo(corpus, embedding)
    gismo.post_documents_item = make_post_publi(lab)
    return gismo


stop_words = ['01', '20plus', 'academia', 'academic', 'academy', 'académie', 'acm', 'activities', 'actualités', 'adresse', 'advances',
      'affichertoutesdepuis', 'ajouter', 'an', 'ancitations', 'and', 'annual', 'annéetrier', 'antipolis', 'are', 'article',
      'articledisponiblesnon', 'articles', 'articles0', 'arxiv', 'as', 'astérisque', 'at', 'attended', 'au', 'auteuradresse',
      'auteurnouveaux', 'auteurnouvelles', 'aux', 'award', 'awarded', 'awards', 'base', 'based', 'be', 'been', 'bibliography',
      'bibliothèquemétriquesalertesparamètresconnexionconnexionobtenir', 'board', 'book', 'born', 'by', 'california', 'called',
      'can', 'celles', 'centrale', 'centre', 'ces', 'cet', 'cette', 'chair', 'chaussées', 'ciarlet', 'citations',
      'citationstrier', 'cited', 'citée', 'cnrs', 'cnrsadresse', 'coauteurscoauteurssuivre', 'collaboration', 'colloquium',
      'collège', 'columbia', 'committee', 'comptabilisées', 'conference', 'contact', 'contributions', 'council', 'cours',
      'course', 'courses', 'dans', 'de', 'des', 'diegoadresse', 'différentes', 'director', 'disponiblessur', 'doi', 'données',
      'doubleles', 'du', 'décompte', 'early', 'earned', 'ecole', 'ed', 'edinburgh', 'elected', 'en', 'english', 'ens', 'envoi',
      'et', 'europaea', 'european', 'events', 'exigences', 'fellow', 'financementcoauteurstout', 'for', 'formerly', 'forum',
      'fr', 'france', 'franceadresse', 'français', 'françois', 'french', 'from', 'fusionnéesle', 'fusionnés', 'google',
      'grenoble', 'gérard', 'habilitation', 'had', 'he', 'her', 'here', 'highly', 'his', 'home', 'hong', 'honorary', 'ici',
      'ieee', 'imag', 'in', 'inclut', 'informatique', 'innovation', 'inria', 'insa', 'institut', 'international', 'invited',
      'is', 'isbn', 'it', 'je', 'jean', 'jour', 'journal', 'july', 'known', 'kong', 'la', 'lab', 'le', 'lecture', 'les',
      'lille', 'liées', 'liés', 'lncs', 'lyon', 'mail', 'maintenant', 'medal', 'media', 'member', 'mises', 'mon', 'monde', 'my',
      'mécanique', 'national', 'ne', 'nombre', 'normale', 'notes', 'notificationsokmon', 'novel', 'of', 'olivier', 'on',
      'opération', 'ordre', 'page', 'pages', 'paper', 'par', 'paraccès', 'parcitée', 'paris', 'paristech', 'partout', 'pas',
      'pdf', 'peut', 'peuvent', 'peux', 'ph', 'phd', 'pierre', 'plus', 'polytechnique', 'ponts', 'pour', 'pp', 'premier',
      'preprint', 'president', 'prix', 'prize', 'proceedings', 'professor', 'profil', 'profilcitée', 'profilma', 'programme',
      'programmes', 'propre', 'présentation', 'publications', 'publiccoauteurstitretriertrier', 'published', 'que', 'qui',
      'received', 'recherche', 'record', 'report', 'research', 'researcher', 'réaliser', 'réessayer',
      'résultatsaideconfidentialitéconditions', 'saclayadresse', 'san', 'scholar', 'scholarchargement', 'school', 'sciences',
      'scientifique', 'scientist', 'selected', 'senior', 'she', 'sigmod', 'silver', 'site', 'slides', 'sont', 'sophia',
      'sorbonne', 'southern', 'speaker', 'springer', 'stanford', 'sud', 'suivants', 'suivies', 'summer', 'supervision',
      'supérieure', 'supérieureadresse', 'sur', 'symposium', 'système', 'tard', 'temps', 'texas', 'that', 'the', 'then',
      'theses', 'titrecitée', 'to', 'transactions', 'travaux', 'télécom', 'un', 'under', 'une', 'univ', 'university',
      'universityadresse', 'université', 'upmc', 'usa', 'using', 'validée', 'verimag', 'verlag', 'veuillez', 'via', 'vol', 'was',
      'with', 'won', 'worked', 'www', 'year', 'école', 'être', 'towards', 'paradigm', 'we', 'this', 'which', 'our', 'proposed',
    'their', 'approach', 'each', 'such', 'show', 'what', 'nous']

sw = stop_words + [str(i) for i in range(2030)]
