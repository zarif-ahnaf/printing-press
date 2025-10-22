from django.urls import path
from django.conf import settings
from ninja import NinjaAPI
from pathlib import Path
import importlib
import sys
from ninja.router import Router
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Get app base name (e.g., 'printing_press')
APP_BASE = __name__.rpartition(".")[0] or __name__

api = NinjaAPI(title="PrintingPress")

VIEWS_DIR = Path(__file__).parent / "views"


def register_routers():
    if not VIEWS_DIR.exists():
        error_msg = f"Views directory not found: {VIEWS_DIR}"
        logger.error(error_msg)
        if settings.DEBUG:
            raise FileNotFoundError(error_msg)
        return

    py_files = sorted(VIEWS_DIR.rglob("*.py"))
    if not py_files:
        warning_msg = f"No Python files found in views directory: {VIEWS_DIR}"
        logger.warning(warning_msg)
        # No need to raise in DEBUG for empty dir—just warn
        return

    for py_file in py_files:
        try:
            rel_path = py_file.relative_to(VIEWS_DIR)
        except ValueError:
            error_msg = f"File {py_file} is not under views directory"
            logger.error(error_msg)
            if settings.DEBUG:
                raise ValueError(error_msg)
            continue

        parts = list(rel_path.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]

        if parts:
            full_module_name = f"{APP_BASE}.views.{'.'.join(parts)}"
            url_prefix = "/".join(parts) + "/"
        else:
            full_module_name = f"{APP_BASE}.views"
            url_prefix = ""

        if full_module_name in sys.modules:
            del sys.modules[full_module_name]

        try:
            module = importlib.import_module(full_module_name)

            if not hasattr(module, "router"):
                error_msg = (
                    f"Module '{full_module_name}' (file: {py_file}) "
                    f"does not define a 'router' attribute. "
                    f"All .py files in 'views/' must define a ninja.Router."
                )
                logger.error(error_msg)
                if settings.DEBUG:
                    raise AttributeError(error_msg)
                continue

            router = module.router
            if not isinstance(router, Router):
                error_msg = (
                    f"'router' in '{full_module_name}' is not a ninja.Router instance. "
                    f"Got: {type(router).__name__}"
                )
                logger.error(error_msg)
                if settings.DEBUG:
                    raise TypeError(error_msg)
                continue

            api.add_router(url_prefix, router)
            logger.debug(
                f"Successfully registered router from {full_module_name} at {url_prefix or '/'}"
            )

        except Exception as e:
            logger.exception(
                f"Failed to load router module '{full_module_name}' "
                f"from file '{py_file}'. Skipping this module."
            )
            if settings.DEBUG:
                raise


# Call registration
register_routers()

urlpatterns = [
    path("", api.urls),
]
