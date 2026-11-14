"""Source adapters. To add a source: create a module with a @register class,
import it below, and add a sample payload under data/raw/<source>/."""
from .base import ADAPTERS, CONTEXT_ADAPTERS, register, resolve_sender  # noqa: F401
from . import github_actions, gmail, google_calendar, slack  # noqa: F401  (registers adapters)
