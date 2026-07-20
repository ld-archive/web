#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# fetch_records.py
# The Lighting Design Archive — LD-Archive.org
# Author: Anthony Arblaster
#
# Pulls records from an InvenioRDM community (Zenodo, or any InvenioRDM
# instance such as Knowledge Commons Works) and writes them, normalised,
# to docs/_data/records.json so the static site can render and search them.
#
# The site never talks to the API at page-load time: this runs at build
# time (see .github/workflows/fetch-records.yml) and the site reads the
# cached JSON. Swapping backends is just a different BASE_URL + COMMUNITY.
#
# Dependency-free (standard library only).
#
# Usage:
#   python3 scripts/fetch_records.py \
#       --base-url https://zenodo.org \
#       --community your-community-slug \
#       --out docs/_data/records.json
# ---------------------------------------------------------------------------

import argparse
import json
import sys
import urllib.parse
import urllib.request

PAGE_SIZE = 100
USER_AGENT = "ld-archive-web/1.0 (+https://ld-archive.org)"


def fetch_page(base_url, community, page):
	"""Fetch one page of records for a community from an InvenioRDM API."""
	query = urllib.parse.urlencode(
		{"communities": community, "size": PAGE_SIZE, "page": page}
	)
	url = base_url.rstrip("/") + "/api/records?" + query
	request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
	with urllib.request.urlopen(request, timeout=30) as response:
		return json.loads(response.read().decode("utf-8"))


def first_or_empty(value):
	"""Return the first element of a list, or an empty string."""
	if isinstance(value, list) and value:
		return value[0]
	return ""


def year_from_date(date_string):
	"""Extract a 4-digit year from an ISO-ish date string."""
	if isinstance(date_string, str) and len(date_string) >= 4:
		return date_string[:4]
	return ""


def normalise_record(hit):
	"""Map one InvenioRDM record onto the archive's flat record shape.

	Standard fields (title, creators, date, DOI, access, keywords) map
	cleanly. Domain-specific fields (venue, company, director) are read
	from InvenioRDM custom fields if present; otherwise left blank until
	the metadata schema is finalised.
	"""
	metadata = hit.get("metadata", {})
	custom = hit.get("custom_fields", {})

	designers = [
		creator.get("person_or_org", {}).get("name")
		or creator.get("name", "")
		for creator in metadata.get("creators", [])
	]
	designers = [name for name in designers if name]

	doi = hit.get("pids", {}).get("doi", {}).get("identifier") or hit.get("doi", "")
	doi_url = "https://doi.org/" + doi if doi else hit.get("links", {}).get("self_html", "")

	files = []
	for name, entry in (hit.get("files", {}).get("entries", {}) or {}).items():
		files.append({"name": name, "size": entry.get("size", "")})

	return {
		"id": str(hit.get("id", "")),
		"title": metadata.get("title", "Untitled"),
		"designers": designers,
		"company": custom.get("ldarchive:company", ""),
		"venue": custom.get("ldarchive:venue", ""),
		"director": custom.get("ldarchive:director", ""),
		"year": year_from_date(metadata.get("publication_date", "")),
		"doi": doi,
		"doi_url": doi_url,
		"source": "Zenodo",
		"access": hit.get("access", {}).get("record", "")
		or metadata.get("access_right", ""),
		"resource_type": (metadata.get("resource_type") or {}).get("title", {}).get(
			"en", ""
		)
		if isinstance(metadata.get("resource_type"), dict)
		else "",
		"description": metadata.get("description", ""),
		"keywords": [
			subject.get("subject", "") if isinstance(subject, dict) else str(subject)
			for subject in metadata.get("subjects", [])
		],
		"files": files,
	}


def fetch_all(base_url, community):
	"""Page through the community and return all normalised records."""
	records = []
	page = 1
	while True:
		payload = fetch_page(base_url, community, page)
		hits = payload.get("hits", {}).get("hits", [])
		if not hits:
			break
		records.extend(normalise_record(hit) for hit in hits)
		total = payload.get("hits", {}).get("total", 0)
		if len(records) >= total or len(hits) < PAGE_SIZE:
			break
		page += 1
	return records


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--base-url", default="https://zenodo.org")
	parser.add_argument("--community", required=True, help="Community slug")
	parser.add_argument("--out", default="docs/_data/records.json")
	args = parser.parse_args()

	try:
		records = fetch_all(args.base_url, args.community)
	except Exception as error:  # noqa: BLE001 — fail loudly in CI
		print("Failed to fetch records: {}".format(error), file=sys.stderr)
		return 1

	with open(args.out, "w", encoding="utf-8") as handle:
		json.dump(records, handle, indent=2, ensure_ascii=False)
		handle.write("\n")

	print("Wrote {} records to {}".format(len(records), args.out))
	return 0


if __name__ == "__main__":
	sys.exit(main())
