# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import datetime
import importlib.metadata
import os
import subprocess

is_tag_release = os.environ.get("READTHEDOCS_VERSION_TYPE") == "tag"


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

this_year = datetime.date.today().year

project = "Tugboat"
author = "tzing"
copyright = f"{this_year}, {author}"

release = importlib.metadata.version("argo-tugboat")
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
]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "shibuya"
html_static_path = ["_static"]

html_theme_options = {
    "accent_color": "tomato",
    "color_mode": "light",
    "github_url": "https://github.com/tzing/tugboat",
}

if not is_tag_release:
    html_theme_options["announcement"] = (
        """
        This is the development version of the documentation.
        """
        # See <a href="https://tugboat.readthedocs.io/en/stable/">stable version</a> for the latest release.
    )
