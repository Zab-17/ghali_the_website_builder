import os
import re
import asyncio

import config


async def deploy_to_vercel(project_name: str) -> dict:
    """Deploy a generated site to Vercel.

    Args:
        project_name: Slug matching the directory in sites/

    Returns:
        Dict with deployment URL and status.
    """
    project_dir = os.path.join(config.SITES_DIR, project_name)

    if not os.path.exists(project_dir):
        return {"error": f"Project directory not found: {project_dir}", "url": ""}

    if not os.path.exists(os.path.join(project_dir, "index.html")):
        return {"error": "No index.html found in project directory", "url": ""}

    try:
        # Deploy to Vercel with production flag
        # Using create_subprocess_exec (not shell) — safe against injection
        proc = await asyncio.create_subprocess_exec(
            "vercel", "deploy", "--yes", "--prod",
            "--name", project_name,
            cwd=project_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        stdout_text = stdout.decode().strip()
        stderr_text = stderr.decode().strip()

        if proc.returncode != 0:
            return {
                "error": f"Vercel deploy failed: {stderr_text or stdout_text}",
                "url": "",
            }

        # The last line of stdout is usually the deployment URL.
        # IMPORTANT: Never synthesize the URL from project_name — Vercel may append
        # a suffix (e.g. "-site") when the requested slug collides with an existing
        # project owned by another team, so {project_name}.vercel.app is NOT a
        # reliable predictor of the live URL.
        deploy_url = stdout_text.split("\n")[-1].strip()

        # Pull the canonical https://…vercel.app production alias out of stdout
        # if present; otherwise fall back to the raw last line.
        alias_match = re.search(r"https://[a-z0-9-]+\.vercel\.app", stdout_text)
        live_url = alias_match.group(0) if alias_match else deploy_url

        return {
            "error": None,
            "url": live_url,
            "project_name": project_name,
        }

    except asyncio.TimeoutError:
        return {"error": "Vercel deploy timed out after 120s", "url": ""}
    except FileNotFoundError:
        return {"error": "Vercel CLI not found. Install with: npm i -g vercel", "url": ""}
