#!/usr/bin/env python3
"""
Batch deployer for Ghali-built sites.
Run this when the Vercel daily deployment limit resets.

Usage:
    python3 deploy_batch.py           # Deploy all pending sites
    python3 deploy_batch.py --dry-run # Check what would be deployed
"""

import asyncio
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.tools.site_deployer import deploy_to_vercel

# Map of (row_index, business_name, slug) for this batch
BATCH = [
    (130, "Kodak - The Spot (AUC)", "kodak-the-spot-auc"),
    (131, "Bali Studios", "bali-studios"),
    (132, "Jannaty Support Services", "jannaty-support-services"),
    (133, "Cherries Preschool", "cherries-preschool-zayed"),
    (134, "Cute Kids Academy", "cute-kids-academy-zayed"),
    (136, "Venti", "venti"),
    (137, "Benzi Car", "benzi-car"),
    (138, "50 wash hub", "50-wash-hub"),
    (139, "Dai Pescatori", "dai-pescatori-maadi"),
    (140, "Candy Smile Center", "candy-smile-center-heliopolis"),
    (141, "Rasha's Hair Salon", "rashas-hair-salon"),
    (142, "Filo Car Care Center", "filo-car-care-center"),
    (143, "My Partner Vet Hospital", "my-partner-vet-hospital"),
    (144, "Invest Home Real Estate", "invest-home-real-estate"),
    (146, "Tabali ElKorba", "tabali-elkorba"),
    (147, "Garcia Restaurant & Cafe", "garcia-restaurant-cafe"),
    (148, "OX Egypt", "ox-egypt"),
    (149, "Coy Restaurant", "coy-restaurant"),
    (150, "The Studio", "the-studio-photography"),
    (151, "Fuji Studios", "fuji-studios"),
]

SITES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sites")


def find_slug(row_index, name, slug_hint):
    """Find the correct site directory for a lead."""
    if slug_hint and os.path.isdir(os.path.join(SITES_DIR, slug_hint)):
        index_path = os.path.join(SITES_DIR, slug_hint, "index.html")
        if os.path.exists(index_path):
            return slug_hint

    # Try to auto-discover from directory names
    name_parts = name.lower().replace("'", "").replace(".", "").split()
    for d in sorted(os.listdir(SITES_DIR), reverse=True):
        dir_path = os.path.join(SITES_DIR, d)
        if not os.path.isdir(dir_path):
            continue
        index_path = os.path.join(dir_path, "index.html")
        if not os.path.exists(index_path):
            continue
        # Check if directory name matches any part of business name
        d_lower = d.lower()
        if any(part in d_lower for part in name_parts[:2]):
            return d

    return None


async def deploy_one(row_index, name, slug):
    """Deploy a single site and return result."""
    print(f"\n  Deploying {name} ({slug})...")
    result = await deploy_to_vercel(slug)

    if isinstance(result, dict) and result.get("error"):
        print(f"  FAILED: {result['error'][:100]}")
        return None
    elif isinstance(result, dict) and result.get("url"):
        print(f"  SUCCESS: {result['url']}")
        return result["url"]
    else:
        url = str(result)
        if "vercel.app" in url:
            print(f"  SUCCESS: {url}")
            return url
        print(f"  UNKNOWN RESULT: {result}")
        return None


async def mark_complete(row_index, url):
    """Mark lead as completed in the sheet."""
    try:
        from agent.tools.sheets_reader import mark_completed
        await mark_completed(row_index, url)
        print(f"  Sheet updated: row {row_index} -> {url}")
    except Exception as e:
        print(f"  Sheet update failed: {e}")
        print(f"  Manual update needed: row {row_index} -> {url}")


async def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("GHALI BATCH DEPLOYER")
    print("=" * 60)

    results = {"deployed": [], "failed": [], "skipped": []}

    for row_index, name, slug_hint in BATCH:
        slug = find_slug(row_index, name, slug_hint)

        if not slug:
            print(f"\n  SKIP {name}: No built site found")
            results["skipped"].append(name)
            continue

        site_dir = os.path.join(SITES_DIR, slug)
        index_path = os.path.join(site_dir, "index.html")

        if not os.path.exists(index_path):
            print(f"\n  SKIP {name}: No index.html in {slug}")
            results["skipped"].append(name)
            continue

        if dry_run:
            print(f"\n  [DRY RUN] Would deploy: {name} -> {slug}")
            continue

        url = await deploy_one(row_index, name, slug)

        if url:
            await mark_complete(row_index, url)
            results["deployed"].append((name, url))
        else:
            results["failed"].append(name)

    # Summary
    print("\n" + "=" * 60)
    print("DEPLOYMENT SUMMARY")
    print("=" * 60)

    if results["deployed"]:
        print(f"\nDEPLOYED ({len(results['deployed'])}):")
        for name, url in results["deployed"]:
            print(f"  {name}: {url}")

    if results["failed"]:
        print(f"\nFAILED ({len(results['failed'])}):")
        for name in results["failed"]:
            print(f"  {name}")

    if results["skipped"]:
        print(f"\nSKIPPED ({len(results['skipped'])}):")
        for name in results["skipped"]:
            print(f"  {name}")

    print(f"\nTotal: {len(results['deployed'])} deployed, "
          f"{len(results['failed'])} failed, "
          f"{len(results['skipped'])} skipped")


if __name__ == "__main__":
    asyncio.run(main())
