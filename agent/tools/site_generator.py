import os
import json
import re

import config


def write_site_files(project_name: str, files: dict[str, str]) -> str:
    """Write generated site files to disk.

    Args:
        project_name: Slug for the project (e.g., 'brand-name')
        files: Dict of filename -> content (e.g., {'index.html': '...', 'styles.css': '...'})

    Returns:
        Absolute path to the project directory.
    """
    project_dir = os.path.join(config.SITES_DIR, project_name)
    os.makedirs(project_dir, exist_ok=True)

    for filename, content in files.items():
        filepath = os.path.join(project_dir, filename)
        # Create subdirectories if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) != project_dir else None
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return project_dir


def read_site_file(project_name: str, filename: str) -> str:
    """Read a generated site file back for editing."""
    filepath = os.path.join(config.SITES_DIR, project_name, filename)
    if not os.path.exists(filepath):
        return f"File not found: {filepath}"
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def slugify(name: str) -> str:
    """Convert a business name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:50]
