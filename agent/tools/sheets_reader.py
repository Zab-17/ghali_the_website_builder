import gspread

import config

# Column indices (0-based) matching Hamed's sheet layout
COL_NAME = 0
COL_CATEGORY = 1
COL_NEIGHBORHOOD = 2
COL_RATING = 3
COL_REVIEW_COUNT = 4
COL_PHONE = 6
COL_WEBSITE = 7
COL_WEBSITE_ISSUES = 8
COL_INSTAGRAM = 9
COL_FACEBOOK = 11
COL_LINKEDIN = 13
COL_STATUS = 14
COL_PRIORITY = 15
COL_CONTACTED = 17  # "Contacted?" column


def _get_sheet() -> gspread.Worksheet:
    gc = gspread.service_account(filename=config.GOOGLE_CREDENTIALS_PATH)
    sh = gc.open_by_key(config.GOOGLE_SHEETS_ID)
    return sh.sheet1


def read_leads(count: int = 1) -> list[dict]:
    """Read next unprocessed leads that have web/social presence."""
    ws = _get_sheet()
    all_rows = ws.get_all_values()

    leads = []
    for row_idx, row in enumerate(all_rows):
        if len(row) <= COL_CONTACTED:
            continue

        name = row[COL_NAME].strip()
        contacted = row[COL_CONTACTED].strip()

        # Skip separator rows, header, already contacted
        if not name or name.startswith("---") or name == "Business Name":
            continue
        if contacted not in ("No", "no", ""):
            continue

        website = row[COL_WEBSITE].strip() if len(row) > COL_WEBSITE else ""
        instagram = row[COL_INSTAGRAM].strip() if len(row) > COL_INSTAGRAM else ""
        facebook = row[COL_FACEBOOK].strip() if len(row) > COL_FACEBOOK else ""

        # Must have at least one web/social presence to scrape
        if not website and not instagram and not facebook:
            continue

        leads.append({
            "row_index": row_idx + 1,  # 1-based for gspread
            "name": name,
            "category": row[COL_CATEGORY].strip() if len(row) > COL_CATEGORY else "",
            "neighborhood": row[COL_NEIGHBORHOOD].strip() if len(row) > COL_NEIGHBORHOOD else "",
            "rating": row[COL_RATING].strip() if len(row) > COL_RATING else "",
            "review_count": row[COL_REVIEW_COUNT].strip() if len(row) > COL_REVIEW_COUNT else "",
            "phone": row[COL_PHONE].strip() if len(row) > COL_PHONE else "",
            "website_url": website,
            "website_issues": row[COL_WEBSITE_ISSUES].strip() if len(row) > COL_WEBSITE_ISSUES else "",
            "instagram_url": instagram,
            "facebook_url": facebook,
            "linkedin_url": row[COL_LINKEDIN].strip() if len(row) > COL_LINKEDIN else "",
            "status": row[COL_STATUS].strip() if len(row) > COL_STATUS else "",
            "priority_score": row[COL_PRIORITY].strip() if len(row) > COL_PRIORITY else "",
        })

        if len(leads) >= count:
            break

    return leads


def mark_lead_in_progress(row_index: int) -> None:
    """Mark a lead as 'In Progress' in the Contacted? column."""
    ws = _get_sheet()
    ws.update_cell(row_index, COL_CONTACTED + 1, "In Progress")


def mark_lead_done(row_index: int, site_url: str) -> None:
    """Mark a lead as done with the deployed site URL."""
    ws = _get_sheet()
    ws.update_cell(row_index, COL_CONTACTED + 1, f"Site: {site_url}")


def find_lead_by_name(business_name: str) -> dict | None:
    """Find a specific lead by business name."""
    ws = _get_sheet()
    all_rows = ws.get_all_values()

    for row_idx, row in enumerate(all_rows):
        if len(row) <= COL_NAME:
            continue
        name = row[COL_NAME].strip()
        if name.lower() == business_name.lower():
            website = row[COL_WEBSITE].strip() if len(row) > COL_WEBSITE else ""
            instagram = row[COL_INSTAGRAM].strip() if len(row) > COL_INSTAGRAM else ""
            facebook = row[COL_FACEBOOK].strip() if len(row) > COL_FACEBOOK else ""

            return {
                "row_index": row_idx + 1,
                "name": name,
                "category": row[COL_CATEGORY].strip() if len(row) > COL_CATEGORY else "",
                "neighborhood": row[COL_NEIGHBORHOOD].strip() if len(row) > COL_NEIGHBORHOOD else "",
                "rating": row[COL_RATING].strip() if len(row) > COL_RATING else "",
                "review_count": row[COL_REVIEW_COUNT].strip() if len(row) > COL_REVIEW_COUNT else "",
                "phone": row[COL_PHONE].strip() if len(row) > COL_PHONE else "",
                "website_url": website,
                "website_issues": row[COL_WEBSITE_ISSUES].strip() if len(row) > COL_WEBSITE_ISSUES else "",
                "instagram_url": instagram,
                "facebook_url": facebook,
                "linkedin_url": row[COL_LINKEDIN].strip() if len(row) > COL_LINKEDIN else "",
                "status": row[COL_STATUS].strip() if len(row) > COL_STATUS else "",
                "priority_score": row[COL_PRIORITY].strip() if len(row) > COL_PRIORITY else "",
            }

    return None
