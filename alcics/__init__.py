"""Top-level package for Analytical Lab Cartography In Computer Science."""

__author__ = """Fabien Mathieu"""
__email__ = 'loufab@gmail.com'
__version__ = '0.1.0'

from alcics.database.hal import HALAuthor
from alcics.database.dblp import DBLPAuthor
from alcics.lab.lab import Lab
from alcics.lab.member import Member
from alcics.lab.publication import Publication
from alcics.utils.common import get_classes

from alcics.gismo import make_gismo
from alcics.search import Search, SearchDocuments, SearchLandmarks, SearchFeatures, search_to_html, search_to_text
