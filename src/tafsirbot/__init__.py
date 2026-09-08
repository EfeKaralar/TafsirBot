"""TafsirBot — AI-powered Quranic commentary assistant.

This package deliberately has no import-time side effects: no ``load_dotenv()``,
no ``logging.basicConfig()``, no ``sys.path`` mutation. Entry points
(``cli/``, ``api/``) are responsible for calling :func:`tafsirbot.logging_config.configure_logging`
and constructing :class:`tafsirbot.settings.Settings`.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
