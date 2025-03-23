# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import datetime
import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "_ext"))

is_tag_release = os.environ.get("READTHEDOCS_VERSION_TYPE") == "tag"


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

this_year = datetime.date.today().year

project = "Tugboat"
author = "tzing"
copyright = f"{this_year}, {author}"

version = importlib.metadata.version("argo-tugboat")
release = version

if not is_tag_release:
    commit = (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode()
        .strip()
    )
    release += f"+{commit}"


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_design",
    "rule_directive",
]

templates_path = ["_templates"]
exclude_patterns = []

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pluggy": ("https://pluggy.readthedocs.io/en/stable/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}


# -- Options for autodoc -----------------------------------------------------
autodoc_default_options = {
    "exclude-members": "model_computed_fields, model_config, model_fields",
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "shibuya"
html_static_path = ["_static"]
html_css_files = [
    "styles/rules.css",
]

html_context = {
    "source_type": "github",
    "source_user": "tzing",
    "source_repo": "tugboat",
}

html_theme_options = {
    "accent_color": "tomato",
    "color_mode": "light",
    "github_url": "https://github.com/tzing/tugboat",
}


if not is_tag_release:
    html_theme_options["announcement"] = (
        """
        This is the development version of the documentation.
        See <a href="https://argo-tugboat.readthedocs.io/en/stable/">stable version</a> for the latest release.
        """
    )
