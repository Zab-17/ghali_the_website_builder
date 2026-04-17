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
        # --name is deprecated; Vercel auto-links via .vercel/project.json
        # Using create_subprocess_exec (not shell) — safe against injection
        proc = await asyncio.create_subprocess_exec(
            "vercel", "deploy", "--yes", "--prod",
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

        # Vercel CLI (50+) prints the per-deployment hash URL to stdout and
        # the clean production alias to stderr (e.g. "✅ Production: https://slug.vercel.app").
        # The hash URL is always gated by Deployment Protection and returns
        # an "Authentication Required" page to the public — so we MUST prefer
        # the alias. Scan both streams.
        combined = stdout_text + "\n" + stderr_text
        all_urls = re.findall(r"https://[a-z0-9-]+\.vercel\.app", combined)

        # Project-scoped hash URLs have the form:
        #   {slug}-{hash}-{team-or-user}-projects.vercel.app
        # The trailing "-projects" is the tell. Filter those out — what remains
        # should be the clean public alias(es).
        public_urls = [u for u in all_urls if not u.endswith("-projects.vercel.app")]

        if public_urls:
            # Shortest wins — e.g. "slug.vercel.app" beats "slug-git-main.vercel.app"
            live_url = min(public_urls, key=len)
        elif all_urls:
            # No alias found — deploy likely did not finish aliasing. Surface
            # an error rather than sending a protected URL to the client.
            return {
                "error": (
                    "Vercel deploy produced only protected hash URLs; no public "
                    f"alias found. Raw output:\n{combined}"
                ),
                "url": "",
            }
        else:
            return {
                "error": f"No .vercel.app URL in deploy output:\n{combined}",
                "url": "",
            }

        return {
            "error": None,
            "url": live_url,
            "project_name": project_name,
        }

    except asyncio.TimeoutError:
        return {"error": "Vercel deploy timed out after 120s", "url": ""}
    except FileNotFoundError:
        return {"error": "Vercel CLI not found. Install with: npm i -g vercel", "url": ""}
