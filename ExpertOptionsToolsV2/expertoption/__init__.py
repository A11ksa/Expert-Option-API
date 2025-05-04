"""
Module for Expert Option related functionality.

Contains asynchronous and synchronous clients,
as well as specific classes for Expert Option trading.
"""

__all__ = ['asyncronous', 'syncronous', 'ExpertOptionAsync', 'ExpertOption']

from . import asyncronous, syncronous
from .asyncronous import ExpertOptionAsync
from .syncronous import ExpertOption
