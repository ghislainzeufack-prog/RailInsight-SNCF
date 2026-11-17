"""Configuration Sphinx pour la documentation RailInsight SNCF."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "RailInsight SNCF"
author = "Equipe RailInsight"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
language = "fr"
html_theme = "alabaster"
