"""Independent public employer discovery from skill/location queries, with no company seeds."""
import argparse,json,re,threading
from pathlib import Path
from datetime import date
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor,as_completed
import campaign
from quality import canonical_url,normalized_name

BASE=Path(__file__).resolve().parent
QUERIES=[
 {"keywords":"Pega","location":"Bengaluru, Karnataka, India"},
 {"keywords":"PRPC","location":"Bangalore, India"},
 {"keywords":"Pega CSSA","location":"India"},
 {"keywords":"Pega","location":"India","f_WT":"2"},
 {"keywords":"Pega decisioning","location":"India"},
 {"keywords":"Pega Constellation","location":"India"},
 {"keywords":"workflow integration Kafka","location":"Bengaluru, Karnataka, India"},
 {"keywords":"Pega","location":"Worldwide","f_WT":"2"},
]
def audit_candidate(job, research_date=None):
    """Add transparent geography/date caveats without guessing remote permission."""
    notes = list(job.get("requirements_unknown", []))
    location = job.get("location", "")
    if re.search(r"\bIndia\b|Bengaluru|Bangalore", location, re.I):
        job["listed_geography"] = "india"
    elif re.search(r"United States|Canada|Poland|Romania|Singapore|Malta|Saudi Arabia|Germany|,\s*(?:TX|AZ)\b", location, re.I):
        job["listed_geography"] = "outside_india"
        notes.append("Listed outside India; relocation, work authorization and permission to work from India are unverified. A remote search filter does not establish India eligibility.")
    else:
        job["listed_geography"] = "unknown"
    title_signals = campaign.experience_signals("", job.get("title", ""))
    if title_signals:
        job["experience_min"] = max(job.get("experience_min") or 0, max(x["minimum_years"] for x in title_signals))
        evidence = job.setdefault("experience_evidence", [])
        for signal in title_signals:
            if signal not in evidence:
                evidence.append(signal)
        notes = [x for x in notes if x not in ("Explicit experience threshold not identified", "Experience threshold")]
        if job["experience_min"] > 4:
            job["fit"] = "stretch"
            notes.append(f"The public title explicitly states {job['experience_min']} years of experience; this exceeds the known four years.")
    try:
        age = (date.fromisoformat(research_date or campaign.now()[:10]) - date.fromisoformat(job["posted_at"][:10])).days
    except (ValueError, KeyError, TypeError):
        pass
    else:
        job["posted_at_age_days"] = age
        job["posted_at_source"] = "LinkedIn public job card"
        if age > 90:
            job["posting_freshness"] = "older_than_90_days"
            notes.append("The public card's posting date is over 90 days old; it is a retained lead, not proof of closure or a freshly opened vacancy.")
    job["requirements_unknown"] = list(dict.fromkeys(notes))
    return job


def discover(output=None,pages=3,detail_limit=45):
    output=Path(output or BASE/'research/fresh_public_jobs.json')
    doc={"research_date":campaign.now()[:10],"scope":"Independent public LinkedIn skill/location queries; no employer names supplied","queries":[],"companies":[],"opportunities":[],"targets":[]}
    client=campaign.PublicClient(threading.Event())
    employers={};jobs={}
    for query in QUERIES:
        for page in range(pages):
            url="https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"+urlencode(dict(query,start=page*25))
            html,diagnostic=client.get(url)
            audit={"query":query["keywords"],"location":query["location"],"page_offset":page*25,"source":"LinkedIn public job cards","url":url,"checked_at":diagnostic["checked_at"],"http_status":diagnostic.get("http_status"),"remote_filter_requested":query.get("f_WT")=="2"}
            doc["queries"].append(audit)
            if html is None:
                audit.update(outcome="blocked_or_unavailable",error=diagnostic.get("error"))
                if diagnostic.get("http_status") == 429:
                    doc.update(status="partial",stop_reason="Public source rate limited; no further requests issued")
                    campaign.save_campaign(doc,output)
                    return doc
                campaign.save_campaign(doc,output)
                break
            cards,raw=campaign.parse_cards(html,{"name":"Independent discovery (broad)"})
            audit.update(outcome="results" if raw else "no_cards",card_count=raw)
            if not raw:
                if html.strip() and not re.search(r"no (?:matching )?jobs|no results",html,re.I):audit["outcome"]="unrecognized_response"
                campaign.save_campaign(doc,output)
                break
            for card in cards:
                # A broad search can return loose matches; company inclusion needs a
                # relevant title here or independently researched evidence elsewhere.
                track=campaign.classify_track(card["title"])
                if track is None:continue
                key=normalized_name(card["company"])
                employer=employers.setdefault(key,{"name":card["company"],"category":"unclassified","aliases":[],"claims":[],"people":[],"hiring_signals":[],"limitations":["A public job card is a hiring lead; current employer application acceptance requires checking.","Remote search filters do not establish eligibility to work from India.","No team headcount or salary inferred.","A listing may advertise a client assignment; it does not alone prove the named poster employs an internal Pega team."]})
                claim={"type":"pega_usage" if track=="pega" else "adjacent_role","text":"Public listing for "+card["title"]+" in "+card["location"]+".","source_url":card["url"],"source_title":card["company"]+" · "+card["title"],"checked_at":diagnostic["checked_at"],"source_date":card.get("posted_at"),"source_kind":"public_job_card","access":"page","confidence":"direct"}
                if not any(c["source_url"]==claim["source_url"] for c in employer["claims"]):
                    employer["claims"].append(claim)
                    employer["hiring_signals"].append({"kind":"public_job_card","description":card["title"],"url":card["url"],"title":card["title"],"location":card["location"],"checked_at":diagnostic["checked_at"],"source_date":card.get("posted_at"),"access":"page","vacancy_confirmed":False,"status":"unverified"})
                job=campaign.make_job(**card,source="Independent LinkedIn public discovery",checked_at=diagnostic["checked_at"])
                if job:
                    job.update(independent_discovery=True,status="candidate",verification_status="candidate",employer_type="unknown")
                    jobs.setdefault(canonical_url(card["url"]),audit_candidate(job,doc["research_date"]))
            doc["companies"]=list(employers.values());doc["opportunities"]=list(jobs.values())
            campaign.save_campaign(doc,output)
            print(json.dumps({"pages":len(doc["queries"]),"employers":len(employers),"roles":len(jobs)}),flush=True)
    ordered=sorted(jobs.values(),key=lambda j:(not bool(re.search(r"bengaluru|bangalore",j["location"],re.I)),j["track"]!="pega",j["company"]))
    doc["detail_scope"]={"requested":min(detail_limit,len(ordered)),"checked":0,"read":0}
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending={pool.submit(campaign.enrich_job,job,client):job for job in ordered[:detail_limit]}
        for future in as_completed(pending):
            original=pending[future]
            try:updated=future.result()
            except campaign.Cancelled:
                doc["detail_scope"]["skipped_rate_limit"] = doc["detail_scope"].get("skipped_rate_limit", 0) + 1
                continue
            except Exception as error:
                updated=dict(original,job_detail_status="unavailable",job_detail_diagnostic={"error":str(error)})
            if updated.get("job_detail_diagnostic", {}).get("http_status") == 429:
                client.stop_event.set()
                doc["stop_reason"] = "Public source rate limited; remaining detail requests skipped"
            jobs[canonical_url(original["url"])]=audit_candidate(updated,doc["research_date"])
            doc["detail_scope"]["checked"]+=1
            doc["detail_scope"]["read"]+=updated.get("job_detail_status")=="read"
            doc["opportunities"]=list(jobs.values())
            campaign.save_campaign(doc,output)
    doc.update(status="partial" if doc.get("stop_reason") else "complete",completed_at=campaign.now())
    campaign.save_campaign(doc,output)
    print(json.dumps({"complete":doc["status"]=="complete","pages":len(doc["queries"]),"employers":len(employers),"roles":len(jobs),"details":doc["detail_scope"]}),flush=True)
    return doc
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--pages",type=int,default=3);parser.add_argument("--details",type=int,default=45)
    args=parser.parse_args();discover(pages=args.pages,detail_limit=args.details)
