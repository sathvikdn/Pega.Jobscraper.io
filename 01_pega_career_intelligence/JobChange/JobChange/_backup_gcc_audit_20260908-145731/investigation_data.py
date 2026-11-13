"""Build the evidence map exclusively from newly researched, source-linked inputs.

A local person, an event attendee and a local vacancy are different observations.
The builder preserves those scopes and never turns a move into replacement hiring.
"""
import copy
import ipaddress
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

BASE = Path(__file__).resolve().parent
FRESH_FILES = ("fresh_people.json", "fresh_ecosystem.json",
               "fresh_consulting.json", "fresh_public_jobs.json",
               "gcc_refresh_20260908.json", "consulting_refresh_20260908.json",
               "root_refresh_20260908.json", "linkedin_refresh_observations_20260908.json",
               "crosscheck_banking_20260908.json", "crosscheck_consulting_20260908.json",
               "crosscheck_remote_20260908.json", "crosscheck_root_20260908.json")
LOCAL = re.compile(r"\b(?:bengaluru|bangalore)\b", re.I)
MOVES = {"employee_move", "employee_departure", "career_move", "job_change", "open_to_work"}
CLOSED = {"closed", "expired", "removed", "unavailable", "inactive", "no_longer_available"}
OPEN = {"open", "active", "page_available", "confirmed_open", "verified_open"}
CATEGORIES = {"gcc", "services", "global", "unclassified"}


def key(value):
    return re.sub("[^a-z0-9]", "", unicodedata.normalize("NFKD", str(value or "")).lower())


def rows(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def strings(value):
    return list(dict.fromkeys(v.strip() for v in rows(value) if isinstance(v, str) and v.strip()))


def token(value):
    return re.sub(r"[\s-]+", "_", str(value or "").strip().lower())


def public_source(url):
    if not isinstance(url, str):
        return False
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if parts.scheme != "https" or not host or parts.username or parts.password:
            return False
        if host.lower() == "localhost" or host.lower().endswith((".localhost", ".local")):
            return False
        try:
            if not ipaddress.ip_address(host).is_global:
                return False
        except ValueError:
            pass
        return True
    except (ValueError, TypeError):
        return False


def source_url(row):
    return next((row.get(k) for k in ("source_url", "url")
                 if public_source(row.get(k))), None)


def canonical_url(url):
    if not public_source(url):
        return ""
    parts = urlsplit(url)
    host = parts.hostname.lower()
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        match = re.search(r"/jobs/view/(?:[^/?]*-)?(\d+)(?:/|$)", parts.path)
        if match:
            return "https://www.linkedin.com/jobs/view/" + match.group(1)
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query)
                             if not k.lower().startswith("utm_") and k.lower() not in {"trk", "trackingid"}))
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def person_key(person):
    url = person.get("profile_url")
    if public_source(url):
        parts = urlsplit(url)
        if parts.hostname == "linkedin.com" or parts.hostname.endswith(".linkedin.com"):
            match = re.match(r"/in/([^/]+)", parts.path, re.I)
            if match:
                return "linkedin:" + match.group(1).lower()
        return "profile:" + canonical_url(url)
    return "observation:" + key(person.get("name")) + "|" + key(person.get("employer_as_stated")) + "|" + canonical_url(person.get("source_url"))


def access(value, status=None):
    value = token(value)
    if value in {"search_index", "search_index_only", "index", "indexed", "index_only"}:
        return "search_index"
    if value in {"page", "direct_page"}:
        return "page"
    if "index" in token(status):
        return "search_index"
    return "unknown"


def unique(records, identity=None):
    seen, result = set(), []
    for record in records:
        ident = identity(record) if identity else json.dumps(record, sort_keys=True, ensure_ascii=True)
        if ident not in seen:
            seen.add(ident)
            result.append(record)
    return result


def normalize_record(raw, filename):
    if not isinstance(raw, dict) or not source_url(raw):
        return None
    record = copy.deepcopy(raw)
    record["source_url"] = source_url(raw)
    record["access"] = access(raw.get("access"), raw.get("status"))
    record["limitations"] = strings([*strings(raw.get("limitations")), *strings(raw.get("not_evidence_of"))])
    record["research_file"] = filename
    return record


def normalize_person(raw, filename):
    person = normalize_record(raw, filename)
    if not person or not person.get("name"):
        return None
    person["profile_url"] = raw.get("profile_url") if public_source(raw.get("profile_url")) else None
    for field in ("title", "employer_as_stated", "location_as_stated", "pega_connection", "work_summary"):
        person.setdefault(field, None)
    profile_source = raw.get("profile_source_url") or person["profile_url"]
    profile_access = access(raw.get("profile_access"))
    if profile_source == person["source_url"] and profile_access == "unknown":
        profile_access = person["access"]
    person["profile_access"] = profile_access
    person["field_sources"] = {}
    for field in ("name", "title", "employer_as_stated", "location_as_stated", "pega_connection", "work_summary"):
        url, how = person["source_url"], person["access"]
        if field == "location_as_stated":
            specific = raw.get("location_source_url") or raw.get("profile_source_url")
            if public_source(specific):
                url = specific
                how = profile_access if specific == profile_source else access(raw.get("location_access"))
        person["field_sources"][field] = [{"source_url": url, "access": how,
                                            "checked_at": person.get("checked_at"),
                                            "research_file": filename}]
    person["field_sources"]["profile_url"] = [{"source_url": profile_source,
                                               "access": profile_access,
                                               "checked_at": person.get("checked_at"),
                                               "research_file": filename}] if public_source(profile_source) else []
    return person


def normalize_signal(raw, filename):
    signal = normalize_record(raw, filename)
    if not signal:
        return None
    raw_kind, raw_type = token(raw.get("kind")), token(raw.get("type"))
    original = token(raw.get("status"))
    signal["status_original"] = raw.get("status")
    signal["vacancy_confirmed_original"] = raw.get("vacancy_confirmed")
    signal["kind_original"] = raw.get("kind") or raw.get("type")
    move = bool({raw_kind, raw_type, original} & MOVES)
    if move:
        kind = "employee_move"
    elif raw_kind in {"employer_job", "public_job_card", "recruiter_post"}:
        kind = raw_kind
    elif raw_type in {"employer_requisition", "employer_job"}:
        kind = "employer_job"
    else:
        kind = "recruiter_post"
    description = raw.get("description") or raw.get("text") or raw.get("title") or ""
    # Explicit historical descriptions qualify status; an old posting date alone
    # does not establish that a still-observed employer requisition has closed.
    historical = ("historical" in original or "historical" in raw_type or
                  any(re.search(r"\bhistorical (?:post|posting|hiring)", s, re.I)
                      for s in [str(description), *signal["limitations"]]))
    closed = original in CLOSED or original.startswith(("closed_", "expired_"))
    if move:
        status = "employee_move"
    elif closed:
        status = "closed"
    elif historical:
        status = "historical"
    elif (raw.get("vacancy_confirmed") is True and kind == "employer_job"
          and signal["access"] == "page" and original in OPEN and check_day(raw)):
        status = "confirmed_open"
    else:
        status = "candidate" if kind == "public_job_card" else "unverified"
    requisition = re.match(r"^Requisition\s+([A-Za-z0-9_-]+):\s*([^;]+)(?:;\s*([^;]+))?",
                           str(description), re.I)
    parsed_title = requisition.group(2).strip() if requisition else None
    parsed_location = requisition.group(3).strip() if requisition and requisition.group(3) else None
    if parsed_location and not LOCAL.search(parsed_location):
        parsed_location = None
    signal["title_basis"] = "explicit" if raw.get("title") else (
        "parsed_requisition_text" if parsed_title else "description_fallback")
    if requisition:
        signal["requisition_id"] = requisition.group(1)
    signal.update(kind=kind, status=status, description=description,
                  text=raw.get("text") or description, url=signal["source_url"],
                  title=raw.get("title") or parsed_title or description,
                  location=raw.get("location") or parsed_location,
                  vacancy_confirmed=status == "confirmed_open")
    signal["evidence_scope"] = raw.get("evidence_scope") or (
        "job_search_card" if kind == "public_job_card" else
        "recruiting_post" if kind == "recruiter_post" else
        "employment_change" if move else "employer_requisition")
    if status == "employee_move":
        signal["limitations"] = strings([*signal["limitations"],
            "An employment change does not establish a replacement vacancy."])
    return signal


def signal_key(signal):
    url = canonical_url(signal["url"])
    if re.match(r"https://www\.linkedin\.com/jobs/view/\d+$", url):
        return url
    return url, key(signal.get("title"))


def check_day(row):
    try:
        return datetime.fromisoformat(str(row.get("checked_at") or "").replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def reconcile_signals(signals):
    grouped = {}
    for signal in signals:
        grouped.setdefault(signal_key(signal), []).append(signal)
    result = []
    rank = {"employee_move": 5, "closed": 4, "historical": 3,
            "confirmed_open": 2, "unverified": 1, "candidate": 0}
    for observations in grouped.values():
        observations = unique(observations)
        # Same-day closure beats an old search card or conflicting open assertion.
        primary = max(enumerate(observations), key=lambda item: (
            check_day(item[1]), rank[item[1]["status"]],
            item[1].get("access") == "page", item[0]))[1]
        merged = copy.deepcopy(primary)
        merged["observations"] = observations
        merged["limitations"] = strings([*primary["limitations"], *[
            "Earlier observation: " + limitation
            for observation in observations if observation is not primary
            for limitation in observation["limitations"]
            if limitation not in primary["limitations"]]])
        result.append(merged)
    return result


def merge_people(people):
    grouped = {}
    for person in people:
        grouped.setdefault(person_key(person), []).append(person)
    result = []
    for ident, observations in grouped.items():
        observations = unique(observations)
        primary = copy.deepcopy(observations[0])
        primary["identity_key"] = ident
        primary["identity_method"] = "public_profile" if not ident.startswith("observation:") else "name_employer_source"
        primary["observations"] = observations
        primary["company_ids"] = strings([o.get("company_id") for o in observations])
        primary["companies"] = strings([o.get("company") for o in observations])
        primary["limitations"] = strings([s for o in observations for s in o.get("limitations", [])])
        primary["work_summaries"] = strings([o.get("work_summary") for o in observations])
        primary["field_sources"] = {}
        for field in {k for o in observations for k in o.get("field_sources", {})}:
            primary["field_sources"][field] = unique([s for o in observations for s in o.get("field_sources", {}).get(field, [])])
        result.append(primary)
    return result


def local_person(person):
    location = str(person.get("location_as_stated") or "")
    if not LOCAL.search(location):
        return False
    # A negative, historical or event mention cannot become a current footprint.
    if re.search(r"\b(?:older|historical|previous|former|event participation)\b", location, re.I):
        return False
    if re.search(r"\b(?:bangalore|bengaluru)\b.{0,35}\b(?:not established|not verified|unconfirmed)\b", location, re.I):
        return False
    if re.search(r"\bnot (?:in |at )?(?:bangalore|bengaluru)\b", location, re.I):
        return False
    return True


def local_claim(claim):
    if claim.get("type") != "bangalore_team" or claim.get("confidence") != "direct":
        return False
    text = str(claim.get("text") or "")
    if re.search(r"\bhistorical\b|\bno (?:active|current|local)\b|\bnot (?:established|verified)\b", text, re.I):
        return False
    return bool(LOCAL.search(text))


def india_remote_lead(signal):
    if signal.get("status") in {"closed", "historical", "employee_move"}:
        return False
    location = str(signal.get("location") or "")
    eligibility = token(signal.get("remote_eligibility"))
    restrictions = str(signal.get("remote_restrictions") or "")
    if eligibility in {"country_restricted", "countryrestricted", "us_only", "us_remote", "uk_only"}:
        return False
    text = " ".join([location, restrictions])
    if re.search(r"\b(?:not (?:in|from)|excluding|except|outside)\s+india\b", text, re.I):
        return False
    if re.search(r"\b(?:us|usa|united states|uk|united kingdom|canada|australia|europe)\b.{0,20}\bonly\b", text, re.I):
        return False
    return eligibility == "india_remote" or bool(
        re.search(r"\b(?:pan[- ]?)?india\b", location, re.I)
        and re.search(r"\bremote\b", location, re.I)
        and not re.search(r"\b(?:hybrid|onsite|on-site|not remote)\b", location, re.I))


def build_map(research_dir=None):
    root = Path(research_dir or BASE / "research")
    groups, queries, inputs, diagnostics = [], [], [], []
    for filename in FRESH_FILES:
        path = root / filename
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        inputs.append(filename)
        for q in rows(doc.get("queries")):
            if isinstance(q, str):
                q = {"query": q}
            if isinstance(q, dict):
                queries.append(dict(q, research_file=filename))
        for raw in rows(doc.get("companies")):
            if not isinstance(raw, dict) or not raw.get("name"):
                continue
            row = copy.deepcopy(raw)
            row["claims"], row["people"], row["hiring_signals"] = [], [], []
            for field in ("claims", "people", "hiring_signals"):
                for item in rows(raw.get(field)):
                    normalizer = normalize_person if field == "people" else normalize_signal if field == "hiring_signals" else normalize_record
                    value = normalizer(item, filename)
                    if value and (field != "claims" or value.get("text")):
                        if field == "claims":
                            value["type"] = token(value.get("type")) or "other"
                            value["confidence"] = token(value.get("confidence")) or "unknown"
                        row[field].append(value)
                    else:
                        diagnostics.append({"research_file": filename, "company": raw["name"],
                                            "field": field, "reason": "Missing valid public source or required content."})
            if not any(row[field] for field in ("claims", "people", "hiring_signals")):
                continue
            row["aliases"] = strings(raw.get("aliases"))
            row["limitations"] = strings(raw.get("limitations"))
            category = token(raw.get("category"))
            row["category"] = category if category in CATEGORIES else "unclassified"
            row["category_observations"] = [{"category": row["category"], "research_file": filename}]
            row["research_files"] = [filename]
            row["_keys"] = {key(n) for n in [row["name"], *row["aliases"]] if key(n)}
            matches = [g for g in groups if row["_keys"] & g["_keys"]]
            if not matches:
                groups.append(row)
                continue
            group = matches[0]
            for other in [*matches[1:], row]:
                if key(group["name"]) in {key(a) for a in other["aliases"]}:
                    group["aliases"].append(group["name"])
                    group["name"] = other["name"]
                group["_keys"].update(other["_keys"])
                group["aliases"].extend([other["name"], *other["aliases"]])
                for field in ("claims", "people", "hiring_signals", "limitations", "research_files", "category_observations"):
                    group[field].extend(other[field])
                if other in groups:
                    groups.remove(other)
    all_observations = []
    for group in groups:
        group.pop("_keys")
        group["id"] = "fresh-" + key(group["name"])
        group["aliases"] = sorted(set([group["name"], *group["aliases"]]))
        group["research_files"] = sorted(set(group["research_files"]))
        specific_categories = {o["category"] for o in group["category_observations"]} & {"gcc", "services"}
        group["category"] = next(iter(specific_categories)) if len(specific_categories) == 1 else (
            "unclassified" if len(specific_categories) > 1 else group["category"])
        if len(specific_categories) > 1:
            group["limitations"].append("Fresh sources disagree on employer category; retained as unclassified.")
        group["claims"] = unique(group["claims"])
        group["hiring_signals"] = reconcile_signals(group["hiring_signals"])
        person_observations = [dict(p, company=group["name"], company_id=group["id"]) for p in group["people"]]
        group["people"] = merge_people(person_observations)
        all_observations.extend(person_observations)
        group["limitations"] = strings(group["limitations"])
        claims, signals = group["claims"], group["hiring_signals"]
        types = {c["type"] for c in claims}
        local_people = any(local_person(p) for p in person_observations)
        eligible = [h for h in signals if h["status"] not in {"closed", "historical", "employee_move"}]
        local_jobs = any(LOCAL.search(str(h.get("location") or "")) for h in eligible)
        verified_team = any(c.get("team_location_verified") is True
                            and c.get("evidence_scope") == "current_employer_team"
                            and c.get("source_kind") == "employer"
                            and c["access"] == "page" and local_claim(c) for c in claims)
        flags = {
            "pega": "pega_usage" in types or any(p.get("pega_connection") for p in person_observations),
            "bangalore": bool(local_people or local_jobs or any(local_claim(c) for c in claims)),
            "bangalore_people": local_people, "bangalore_job_lead": bool(local_jobs),
            "bangalore_team_verified": verified_team,
            "india_remote_lead": any(india_remote_lead(h) for h in eligible),
            "project": "project" in types, "people": bool(group["people"]),
            "hiring": any(h["vacancy_confirmed"] for h in signals),
            "hiring_lead": bool(eligible),
            "historical_hiring": any(h["status"] in {"closed", "historical"} for h in signals),
            "employer_job": any(h["kind"] == "employer_job" and h["vacancy_confirmed"] for h in signals),
        }
        group["flags"] = flags
        group["bangalore_scope"] = "verified_employer_team" if verified_team else "documented_connection_only" if flags["bangalore"] else "not_established"
        group["priority_reason"] = (
            "An employer application page was available when checked; confirm current hiring, requirements and budget."
            if flags["hiring"] else
            "A Bengaluru job lead needs a current requisition check; team allocation and budget are unconfirmed."
            if local_jobs else
            "A Bengaluru professional or geographic connection is documented; current team allocation remains unverified."
            if flags["bangalore"] else
            "Documented project or professional evidence; establish local eligibility and current hiring.")
        group["current_team_size"] = None
    groups.sort(key=lambda g: (not g["flags"]["hiring"], not(g["flags"]["pega"] and g["flags"]["bangalore"]),
                               not g["flags"]["hiring_lead"], not g["flags"]["project"], g["name"].lower()))
    all_people = merge_people(all_observations)
    source_urls = {r["source_url"] for g in groups for field in ("claims", "people", "hiring_signals")
                   for r in g[field]}
    for g in groups:
        for signal in g["hiring_signals"]:
            source_urls.update(o["source_url"] for o in signal["observations"])
    for p in all_people:
        source_urls.update(o["source_url"] for o in p["observations"])
        source_urls.update(s["source_url"] for sources in p["field_sources"].values() for s in sources
                           if public_source(s.get("source_url")))
    signals = [h for g in groups for h in g["hiring_signals"]]
    return {
        "schema_version": 2, "research_date": "2026-09-08",
        "basis": "Fresh public skill/location searches and source-linked professional, customer, partner and job evidence. No legacy catalogue used as evidence.",
        "inputs": inputs, "companies": groups, "people": all_people, "queries": queries,
        "diagnostics": diagnostics,
        "stats": {
            "companies": len(groups), "people_records": len(all_people),
            "people_observations": len(all_observations),
            "unique_linkedin_profiles": sum(p["identity_key"].startswith("linkedin:") for p in all_people),
            "source_urls": len(source_urls), "query_records": len(queries),
            "bangalore_companies": sum(g["flags"]["bangalore"] for g in groups),
            "verified_bangalore_teams": sum(g["flags"]["bangalore_team_verified"] for g in groups),
            "companies_with_india_remote_leads": sum(g["flags"]["india_remote_lead"] for g in groups),
            "companies_with_hiring_signals": sum(g["flags"]["hiring_lead"] for g in groups),
            "companies_with_confirmed_vacancies": sum(g["flags"]["hiring"] for g in groups),
            "confirmed_vacancies": sum(h["vacancy_confirmed"] for h in signals),
            "hiring_signal_statuses": dict(Counter(h["status"] for h in signals)),
            "project_companies": sum(g["flags"]["project"] for g in groups),
            "categories": dict(Counter(g["category"] for g in groups)),
        },
        "definitions": {
            "bangalore_companies": "Companies with a documented professional or job connection; not a count of proven Bengaluru Pega teams.",
            "hiring": "A page-observed employer requisition explicitly confirmed available; closed/history/move/index-only records do not qualify.",
            "hiring_lead": "A recruiting or job lead without an explicit closed/historical/move status; may require current confirmation.",
            "people_records": "Deduplicated public-profile identities or name/employer/source identities; all distinct observations retained.",
        },
        "limitations": [
            "Public discovery is bounded, not every employee or vacancy on LinkedIn.",
            "A checked date records evidence examination, not certainty of current employment.",
            "A local person, event attendee or role does not establish a complete local Pega team.",
            "Projects may be global; local project allocation needs separate evidence.",
            "Employee moves and open-to-work posts never establish replacement vacancies.",
            "No headcount, retention rate or salary budget is inferred from profile counts.",
            "Page and search-index access remain attached to individual and field-specific sources.",
        ],
    }


if __name__ == "__main__":
    data = build_map()
    (BASE / "research/independent_map.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(data["stats"]))
