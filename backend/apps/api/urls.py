from django.urls import path
from ninja import NinjaAPI
from pathlib import Path
import importlib
from ninja.router import Router

# Get app base name (e.g., 'printing_press')
APP_BASE = __name__.rpartition(".")[0] or __name__

api = NinjaAPI(title="PrintingPress")

VIEWS_DIR = Path(__file__).parent / "views"


def register_routers():
    if not VIEWS_DIR.exists():
        raise RuntimeError(f"Views directory not found: {VIEWS_DIR}")

    py_files = sorted(VIEWS_DIR.rglob("*.py"))
    if not py_files:
        raise RuntimeError(f"No Python files found in views directory: {VIEWS_DIR}")

    for py_file in py_files:
        # These are always safe to compute
        try:
            rel_path = py_file.relative_to(VIEWS_DIR)
        except ValueError as e:
            raise RuntimeError(f"File {py_file} is not under views directory") from e

        parts = list(rel_path.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]

        # Build module name — this is just string ops, should not fail
        if parts:
            full_module_name = f"{APP_BASE}.views.{'.'.join(parts)}"
        else:
            full_module_name = f"{APP_BASE}.views"

        url_prefix = "/".join(parts) + "/" if parts else ""

        try:
            module = importlib.import_module(full_module_name)

            if not hasattr(module, "router"):
                raise AttributeError(
                    f"Module '{full_module_name}' (file: {py_file}) "
                    f"does not define a 'router' attribute. "
                    f"All .py files in 'views/' must define a ninja.Router."
                )

            router = module.router
            if not isinstance(router, Router):
                raise TypeError(
                    f"'router' in '{full_module_name}' is not a ninja.Router instance. "
                    f"Got: {type(router).__name__}"
                )

            api.add_router(url_prefix, router)

        except Exception as import_error:
            # Now full_module_name and py_file are guaranteed to be defined
            raise RuntimeError(
                f"Failed to load router module '{full_module_name}' "
                f"from file '{py_file}'."
            ) from import_error


register_routers()

urlpatterns = [
    path("", api.urls),
]
