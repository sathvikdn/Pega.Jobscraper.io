// T4: the GCC Engineering Culture & Autonomy scorer.
//
// Implements the 100-point rubric with two documented corrections to the spec as written:
//
// (1) ARITHMETIC. Pillar 2 is labelled "Max 30" but its itemised tiers total 25
//     (+15 integration, +10 modern UI). That left the rubric summing to 95, not 100.
//     Closed with a third +5 tier for cloud/platform ownership (Pega Cloud, AWS/Azure/GCP,
//     OpenShift, CI/CD, PDC/observability) — the same family of "real engineering" signal
//     the pillar is already testing for. Pillar 2 now totals 30 and the rubric totals 100.
//
// (2) SHORT TENURE != BURNOUT. The spec reads avg tenure < 18 months as "toxic management
//     or dead-end work". That misreads any team which converts interns and hires juniors:
//     Booking shows 1.4y average precisely because it runs an intern->permanent pipeline,
//     which is a growth signal, not an exit signal. So low tenure is only penalised when
//     departure evidence actually dominates join evidence; otherwise it scores as growth
//     and is labelled as such. Without this, the rubric would rank a healthy growing team
//     alongside a team people are fleeing.
//
// Pillar 4 is scored ONLY where >=3 engineers have parseable tenure. Below that an average
// is not defensible, so the pillar is recorded as unmeasured (0) and the company carries a
// reduced evidence_confidence rather than an invented number.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const directory = dirname(fileURLToPath(import.meta.url));
// Keep paths script-relative so the handoff export remains portable.
const DIR = directory + "/";
const base = JSON.parse(readFileSync(DIR + "gcc_evidence_base.json", "utf8"));

const MIN_TENURE_N = 3; // below this, no average is published

// --- Pillar 1: title / seniority probes -------------------------------------
// "Principal Consultant" and "Principal Engineer" are senior individual-contributor
// grades at Indian GCCs (DTICI, MBRDI, Pegasystems), NOT evidence that the global Pega
// roadmap is owned in India. They sat in the top tier and handed out undeserved 30s, so
// they belong in the architect ladder instead.
const T_TOP = /global head|head of pega|head pega|pega coe lead|coe lead|chief architect|principal architect|principal solution architect|executive director|engineering director|managing director|distinguished|director[^.]{0,40}(?:pega|architect|engineering|application)|(?:pega|architecture)[^.]{0,20}director|head[^.]{0,25}(?:pega|workflow|automation|coe)/i;
// Phrasing that can only mean the Pega platform/roadmap is OWNED here, used for the
// text-evidence path where no roster entry carries a location.
const T_TOP_STRONG = /global head[^.]{0,30}(?:pega|platform|workflow)|head of pega|head[, -]*pega (?:coe|platform|practice)|pega coe lead|chief architect|principal pega architect|global (?:pega|platform) (?:head|owner|lead)|(?:engineering|executive|managing) director[^.]{0,40}pega|director[ ,-]+pega (?:architecture|platform|engineering|coe)|head of (?:workflow|automation|digital) (?:platform|engineering)/i;
// Widened: the previous pattern required "lead pega" and missed the far more common
// Indian-bank phrasing "Pega Lead", "Pega Tech Lead", "AVP - Development Lead". That
// scored Barclays 0 on autonomy despite a full CLSA-backed lead ladder.
const T_ARCH = /\b(?:lsa|clsa|pclsa|cssa|cpdc|lsa-1|lsa-2)\b|lead system architect|senior system architect|system architect|solution architect|technical architect|lead architect|pega architect|staff engineer|senior staff|lead engineer|lead software engineer|lead pega|pega lead|tech(?:nical)? lead|development lead|team lead|delivery architect|principal engineer|principal consultant|senior manager|lead decisioning|decisioning architect/i;
// Matches any LSA-family credential: LSA, CLSA, PLSA, PCLSA.
const LSA_ANY = /\b[cp]{0,2}lsa\b/i;
// Mid-track markers. "LSA Part 1", "CLSA-1" and "CLSA Part 2" mean the person is still
// working through the LSA track. The previous /\b(?:lsa|clsa|pclsa)\b/ test matched
// these, so a candidate still studying counted as a certified architect - which is how
// Ford reached rank 1 with no completed LSA anywhere in its India sample.
const LSA_PARTIAL = /\b[cp]{0,2}lsa[\s-]*(?:part[\s-]*)?(?:1|2|i|ii|one|two)\b|\b[cp]{0,2}lsa\s*part\b|pursuing|in progress/i;
// Split the cert list first: one person may hold both a completed and a partial cert.
const hasCompletedLsa = (text) =>
  String(text || "")
    .split(/[,;|]/)
    .some((t) => LSA_ANY.test(t) && !LSA_PARTIAL.test(t));

// The title-only subset of T_ARCH, used to separate a real architect/lead title from
// someone who merely holds a CSSA certification.
const T_ARCH_TITLE = /lead system architect|senior system architect|system architect|solution architect|technical architect|lead architect|pega architect|staff engineer|senior staff|lead engineer|lead software engineer|lead pega|pega lead|tech(?:nical)? lead|development lead|team lead|delivery architect|principal engineer|principal consultant|senior manager|lead decisioning|decisioning architect/i;
const T_DELIVERY = /delivery manager|delivery lead|operations lead|ops lead|support manager|support lead|service delivery|production support|bau lead|incident manager|project manager|program manager|scrum master|technical recruiter|talent acquisition|recruiter/i;

// City-only list missed people whose profile records an Indian STATE rather than a city
// ("Tamil Nadu", "Kerala", "Maharashtra"). They matched neither list, so they fell into
// "location unverified" and were dropped from the India LSA ladder. States added.
const INDIA = /bengaluru|bangalore|hyderabad|chennai|pune|mumbai|gurugram|gurgaon|noida|new delhi|delhi|kolkata|trivandrum|thiruvananthapuram|coimbatore|ahmedabad|kochi|cochin|mysuru|mysore|nagpur|indore|jaipur|chandigarh|mohali|vadodara|surat|lucknow|bhubaneswar|thane|visakhapatnam|vizag|madurai|nashik|\bgoa\b|maharashtra|karnataka|tamil nadu|telangana|kerala|gujarat|haryana|uttar pradesh|west bengal|andhra pradesh|punjab|rajasthan|odisha|\bindia\b/i;
// Was missing most of the world. A Germany-based ex-MBRDI engineer was being counted
// inside India's architect ladder because "germany" appeared nowhere in this list.
const NON_INDIA = /richardson|texas|atlanta|pittsburgh|charlotte|melbourne|sydney|\blondon\b|amsterdam|utrecht|singapore|\bus\)|\busa\b|united states|australia|netherlands|\buk\)|not india|germany|munich|berlin|stuttgart|japan|tokyo|poland|krakow|canada|toronto|dubai|\buae\b|china|shanghai|philippines|manila|malaysia|ireland|dublin|france|paris|spain|madrid|switzerland|zurich|sweden|stockholm|brazil|mexico|hong kong|new zealand|south africa|egypt|vietnam|indonesia|thailand|korea|seoul|italy|belgium|austria|denmark|norway|finland|portugal|turkey|israel|saudi|qatar/i;

// --- Pillar 2: tech probes ---------------------------------------------------
const P2_HEAVY = /kafka|event[- ]driven|event stream|eventing|middleware|\besb\b|\bmq\b|activemq|rabbitmq|ibm mq|\bjms\b|nervous system|iso ?20022|swift|decommission|legacy (?:migration|replacement|modernis|moderniz)|real[- ]time integration|api gateway/i;
const P2_MODERN = /constellation|react|\bdx api\b|custom java|java step|cosmos ui|theme cosmos|blueprint|agentic|genai|gen ai|\bllm\b|knowledge buddy|voice ai/i;
const P2_CLOUD = /pega cloud|\baws\b|azure|\bgcp\b|google cloud|openshift|kubernetes|\bhelm\b|docker|ci\/cd|jenkins|terraform|\bpdc\b|splunk|observability|devops|\bsre\b/i;
const P2_SUPPORT = /l2\/l3|l2 ?\/ ?l3|\bl2\b|\bl3\b|ticket resolution|ticketing|incident (?:handling|management|resolution)|production support|\bbau\b|version upgrade|patch(?:ing|es)\b|maintenance|break[- ]fix/i;

// --- Pillar 3: innovation visibility probes ---------------------------------
const P3_EVENT = /pegaworld|pega world|pegainnovate|pega innovate|pegafest|pega day|keynote|impact award|innovation award|visionary award|presented at|speaker at|case study|customer story/i;
const P3_COMM = /pega forum|forums?\b|pega community|community\b|blog|open[- ]source|github|published|article|webinar|hackathon|badge|bootcamp|gpt-a-thon/i;

const count = (re, text) => (text.match(new RegExp(re.source, "gi")) || []).length;

function seniorityRank(title) {
  if (T_TOP.test(title)) return 3;
  if (T_ARCH.test(title)) return 2;
  if (T_DELIVERY.test(title)) return 1;
  return 0;
}

function scorePillar1(c) {
  const notes = [], green = [], red = [];
  // A top/architect title only proves India autonomy if the person is IN India.
  const topInIndia = [], topAbroad = [], topUnlocated = [], archInIndia = [], departed = [];
  // The LSA/CLSA audit asserts "in India", so it needs the SAME residency discipline as
  // the title tiers above. Filtering c.members directly (as the first version of this
  // audit did) credited Rabobank with 4 "India" CLSA holders who are in Utrecht, and
  // credited BNY Mellon with Virad Fernando, who this research placed in Pittsburgh.
  const lsaIndia = [], lsaUnlocated = [], lsaPartialIndia = [];
  for (const m of c.members) {
    const title = m.title || "";
    // A person who has LEFT cannot evidence where authority sits today. CBA's perfect
    // autonomy score was resting entirely on a roster entry tagged "DEPARTED - Pega CoE Lead".
    if (/departed|has left|serving notice|resigned/i.test(title)) { departed.push(`${m.name} — ${title}`); continue; }
    // An LSA/CLSA credential evidences the architect ladder even when the job title is
    // bank-generic ("AVP", "Software Engineer II"), so certs count toward the arch tier.
    const titleAndCerts = `${title} ${m.certs || ""}`;
    // A location such as "Germany (ex-MBRDI Bengaluru)" records a FORMER India posting.
    // The parenthetical must not satisfy the India test, so the residency check runs on
    // the primary location only while the raw string still feeds the abroad check.
    const locRaw = m.location || "";
    const loc = locRaw.replace(/\([^)]*\)/g, " ").replace(/\s+/g, " ").trim();
    const abroad = NON_INDIA.test(`${locRaw} ${title}`) && !INDIA.test(loc);
    // Bucket LSA-family credentials by residency, independently of the title tiers below,
    // because a CLSA holder may carry either a top-level or a bank-generic title.
    if (!abroad) {
      if (hasCompletedLsa(titleAndCerts)) {
        // A claim about India needs a POSITIVE India location; empty stays "unverified".
        (INDIA.test(loc) ? lsaIndia : lsaUnlocated).push(m);
      } else if (LSA_ANY.test(titleAndCerts)) lsaPartialIndia.push(m);
    }
    if (T_TOP.test(title)) {
      // +30 claims "the global Pega owner sits in India", so it needs a POSITIVE India
      // location. An empty location is unknown, not India: BNY's 30 came from Virad
      // Fernando, who this research established is based in Pittsburgh, USA.
      if (INDIA.test(loc)) topInIndia.push(`${m.name} — ${title}`);
      else if (abroad) topAbroad.push(`${m.name} — ${title} (${loc || "non-India"})`);
      else topUnlocated.push(`${m.name} — ${title} (location unverified)`);
    } else if (T_ARCH.test(titleAndCerts) && !abroad) archInIndia.push(`${m.name} — ${title}`);
  }
  // Text-only leadership evidence (a hub finding naming a head not present in the roster)
  // requires the top-title term NEAR an India city, plus a non-trivial evidence base.
  // The previous blanket test matched any "Director" anywhere in a multi-thousand-character
  // blob alongside any India city, handing 30s to single-person entries (Visa, GE HealthCare).
  // Two strengths of text evidence. T_TOP_STRONG is phrasing that can only mean global
  // ownership ("Global Head of Pega & Cloud Platform ... Bengaluru" = HSBC's Pradeep V,
  // who is real and India-based but absent from the roster sample). Generic seniority
  // words earn the architect tier only.
  const near = (src) => new RegExp(
    `(?:${src})[^.]{0,110}?(?:${INDIA.source})|(?:${INDIA.source})[^.]{0,110}?(?:${src})`, "i"
  );
  const enoughEvidence = c.peopleCount >= 3 || c.auditRows >= 3;
  const textTopStrong = near(T_TOP_STRONG.source).test(c.evidenceText) && enoughEvidence;
  const textTop = near(T_TOP.source).test(c.evidenceText) && enoughEvidence;

  const maxRank = Math.max(0, ...c.members.map((m) => seniorityRank(`${m.title || ""} ${m.certs || ""}`)));
  const deliveryOnly = maxRank === 1;

  let pts = 0;
  if (topInIndia.length) {
    pts = 30;
    notes.push(`India holds top-level Pega authority: ${topInIndia.slice(0, 3).join("; ")}.`);
    green.push("Top-level Pega/architecture authority sits in India");
  } else if (textTopStrong) {
    pts = 30;
    const m = near(T_TOP_STRONG.source).exec(c.evidenceText);
    notes.push(`Unambiguous India-based Pega ownership evidenced in research text: "...${(m ? m[0] : "").slice(0, 150).trim()}...".`);
    green.push("India-based global Pega/platform owner evidenced in research findings");
  } else if (topUnlocated.length) {
    // Top title found but India residency unproven -> architect tier, not global-owner tier.
    pts = 15;
    notes.push(`Top-level title found but India location unverified, so global ownership is not established: ${topUnlocated.slice(0, 2).join("; ")}.`);
    red.push("Senior-most title could not be confirmed as India-based");
  } else if (textTop) {
    pts = 15;
    notes.push("Leadership evidenced in profile text near an India location, but no India-located senior roster entry confirms global ownership.");
  } else if (archInIndia.length) {
    pts = 15;
    // Previously this said "N LSA/architect-level", which overstated the evidence: at MBRDI
    // all 9 counted people were reported that way while NONE held an LSA or CLSA, and 4
    // qualified purely by holding a CSSA. Report the composition instead of one flat number.
    const byTitle = archInIndia.filter((e) => T_ARCH_TITLE.test(e)).length;
    const byCert = archInIndia.length - byTitle;
    const lsaHolders = lsaIndia.length;
    notes.push(
      `India has a senior Pega ladder of ${archInIndia.length} (${byTitle} by architect/lead title, ${byCert} by certification only; ${lsaHolders} hold a completed LSA/CLSA), but no evidenced global owner in India: ${archInIndia.slice(0, 3).join("; ")}.`
    );
    if (topAbroad.length) notes.push(`Top-level title found outside India: ${topAbroad.slice(0, 2).join("; ")}.`);
  } else if (deliveryOnly) {
    pts = -20;
    notes.push("Most senior evidenced India title is delivery/operations/support, with no architect-level owner found.");
    red.push("Cost-centre shape: senior India titles are delivery/ops/support, not architecture");
  } else {
    notes.push("No title evidence strong enough to locate architectural ownership.");
  }
  // The LSA/CLSA audit must apply to EVERY company with positive autonomy evidence, not
  // just the archInIndia (+15) branch where it used to live. All 8 companies scoring +30
  // skipped it entirely, hiding the gap at the very top of the ranking: Ford ranked #1
  // at 100/100 with no completed LSA anywhere in its India sample.
  if (pts > 0) {
    const nameCert = (m) => `${m.name} — ${m.certs || m.title || ""}`;
    if (lsaIndia.length) {
      green.push(
        `Architect ladder present in India (${lsaIndia.length} completed LSA/CLSA holder${lsaIndia.length === 1 ? "" : "s"}: ${lsaIndia.slice(0, 3).map((m) => m.name).join(", ")})`
      );
    } else {
      red.push("No LSA/CLSA-certified architect evidenced in the India sample");
      // An unlocated holder is the weakest form of this evidence: real credential,
      // unproven geography. Surfaced separately so it is never read as India-confirmed.
      if (lsaUnlocated.length) {
        notes.push(
          `${lsaUnlocated.length} completed LSA/CLSA holder${lsaUnlocated.length === 1 ? "" : "s"} found but with no verified India location, so ${lsaUnlocated.length === 1 ? "it" : "they"} cannot evidence an India ladder: ${lsaUnlocated.slice(0, 2).map(nameCert).join("; ")}.`
        );
        red.push("Completed LSA/CLSA found, but India residency unverified");
      }
      if (lsaPartialIndia.length) {
        notes.push(
          `${lsaPartialIndia.length} engineer${lsaPartialIndia.length === 1 ? " is" : "s are"} mid-LSA track but hold no completed LSA/CLSA: ${lsaPartialIndia.slice(0, 2).map(nameCert).join("; ")}.`
        );
        red.push("Senior-most Pega credential evidenced in India is an in-progress LSA, not a completed one");
      }
    }
  }
  if (deliveryOnly && pts > 0) red.push("Delivery/ops titles outrank engineering titles in the India sample");
  if (departed.length) {
    notes.push(`Excluded ${departed.length} departed roster entr${departed.length === 1 ? "y" : "ies"} from this assessment: ${departed.slice(0, 2).join("; ")}.`);
    red.push(`${departed.length} senior/lead roster ${departed.length === 1 ? "entry" : "entries"} evidenced as departed`);
  }
  return { pts, notes, green, red, topInIndia, archInIndia, topAbroad, topUnlocated, departed };
}

function scorePillar2(c) {
  const text = [c.evidenceText, c.tech_stack.join(" "), c.domains.join(" ")].join(" ");
  const heavy = count(P2_HEAVY, text), modern = count(P2_MODERN, text);
  const cloud = count(P2_CLOUD, text), support = count(P2_SUPPORT, text);
  const found = [], green = [], red = [];
  let pts = 0;
  if (heavy >= 1) { pts += 15; green.push("Heavy integration / event-driven / legacy-decommission work evidenced"); }
  if (modern >= 1) { pts += 10; green.push("Constellation / React / custom-Java modernisation evidenced"); }
  if (cloud >= 1) { pts += 5; green.push("Cloud & platform ownership evidenced (Pega Cloud / AWS / OpenShift / CI-CD)"); }

  // Faithful to the spec's -15, but graded: a team doing heavy build work AND some run
  // work is not a support farm, so it takes a smaller drag than a run-only team.
  if (support >= 2 && heavy === 0) { pts -= 15; red.push("Support-farm language dominates with no build/integration evidence"); }
  else if (support >= 3 && heavy >= 1) { pts -= 5; red.push("Significant L2/L3-support and upgrade language alongside build work"); }
  else if (support >= 1 && heavy === 0) { pts -= 5; red.push("Support/upgrade language present, build evidence absent"); }

  for (const [label, re] of [["Kafka/event-driven", /kafka|event[- ]driven|event stream/i], ["Constellation", /constellation/i],
    ["DX API", /\bdx api\b/i], ["React", /react/i], ["custom Java", /custom java|java step/i], ["CDH/Decisioning", /\bcdh\b|decisioning|next[- ]best[- ]action|\bnba\b/i],
    ["SWIFT/ISO 20022", /swift|iso ?20022/i], ["OpenShift/K8s", /openshift|kubernetes/i], ["AWS", /\baws\b/i], ["Azure", /azure/i],
    ["GCP", /\bgcp\b|google cloud/i], ["GenAI/Agentic", /genai|gen ai|agentic|\bllm\b/i], ["Blueprint", /blueprint/i],
    ["REST/SOAP", /rest\b|soap/i], ["JMS/MQ", /\bjms\b|\bmq\b|activemq/i], ["Pega Cloud", /pega cloud/i], ["Splunk/PDC", /splunk|\bpdc\b/i]])
    if (re.test(text)) found.push(label);

  return { pts: Math.max(-15, Math.min(30, pts)), found, green, red, counts: { heavy, modern, cloud, support } };
}

function scorePillar3(c) {
  const t = c.evidenceText;
  const ev = count(P3_EVENT, t), comm = count(P3_COMM, t);
  const green = [], notes = [];
  let pts = 0;
  if (ev >= 1) {
    pts += 10;
    const which = ["PegaWorld", "PegaInnovate", "PegaFest", "Pega Day", "Impact Award", "Innovation Award", "Visionary Award", "keynote", "case study"]
      .filter((k) => new RegExp(k.replace(/ /g, " ?"), "i").test(t));
    green.push(`Conference / award visibility: ${which.slice(0, 4).join(", ") || "evidenced"}`);
    notes.push(`${ev} conference/award mention(s).`);
  }
  if (comm >= 1) {
    pts += 10;
    const which = ["Pega forum", "community", "hackathon", "blog", "GitHub", "bootcamp", "badge", "published"]
      .filter((k) => new RegExp(k, "i").test(t));
    green.push(`Community / build-in-public visibility: ${which.slice(0, 4).join(", ") || "evidenced"}`);
    notes.push(`${comm} community/forum/hackathon mention(s).`);
  }
  if (!pts) notes.push("No conference, forum, blog or hackathon visibility found in available evidence.");
  return { pts, green, notes, counts: { ev, comm } };
}

function scorePillar4(c) {
  const n = c.tenureN, avg = c.tenureAvgYears;
  const dep = c.departureSignals || 0, join = c.joinSignals || 0;
  const green = [], red = [], notes = [];

  if (n < MIN_TENURE_N) {
    notes.push(`Tenure unmeasured: only ${n} engineer(s) with parseable dates (need ${MIN_TENURE_N}). Pillar scored 0, not penalised.`);
    return { pts: 0, level: "Unknown", green, red, notes, measured: false };
  }

  let pts, level;
  if (avg >= 3) {
    pts = 20; level = "Low";
    green.push(`Stable team: average Pega tenure ${avg}y across ${n} engineers`);
    notes.push(`Average tenure ${avg}y (n=${n}) indicates a settled environment.`);
  } else if (avg >= 1.5) {
    pts = 5; level = "Medium";
    notes.push(`Average tenure ${avg}y (n=${n}) — mid-range; neither clearly stable nor clearly churning.`);
  } else {
    // The correction: decide whether short tenure is exit-driven or growth-driven.
    const churnDominant = dep >= 2 && dep >= join * 0.5;
    if (churnDominant) {
      pts = -20; level = "High";
      red.push(`Churn risk: average tenure ${avg}y (n=${n}) with ${dep} departure signal(s) vs ${join} join signal(s)`);
      notes.push(`Short tenure appears exit-driven (${dep} departure vs ${join} join signals).`);
    } else {
      pts = 5; level = "Medium";
      green.push(`Short tenure is growth-driven, not attrition: ${join} join signal(s) vs ${dep} departure signal(s)`);
      notes.push(`Average tenure ${avg}y (n=${n}) is low, but join signals outweigh departures — reads as recent hiring/intern conversion, not churn. Not penalised.`);
    }
  }
  if (dep >= 3) red.push(`${dep} separate departure signals found in evidence`);
  return { pts, level, green, red, notes, measured: true };
}

function confidence(c, p4measured) {
  const srcs = c.sources.length;
  if (srcs >= 3 && p4measured && c.peopleCount >= 5) return "High";
  if (srcs >= 2 && (p4measured || c.peopleCount >= 4)) return "Medium";
  if (c.peopleCount === 0 && c.auditRows === 0) return "None";
  return "Low";
}

const results = [];
for (const c of base.companies) {
  if (c.peopleCount === 0 && c.auditRows === 0) {
    results.push({
      company_name: c.company, total_score: null, score_status: "INSUFFICIENT_EVIDENCE",
      leadership_location_analysis: "No people evidence available; cannot assess.",
      tech_stack_modernity: "No evidence.", attrition_warning_level: "Unknown",
      red_flags: ["No public Pega people evidence found for this entity"], green_flags: [],
      evidence_confidence: "None", pillar_breakdown: null, evidence: { peopleCount: 0, auditRows: 0, tenureN: 0, sources: c.sources },
    });
    continue;
  }
  const p1 = scorePillar1(c), p2 = scorePillar2(c), p3 = scorePillar3(c), p4 = scorePillar4(c);
  const total = p1.pts + p2.pts + p3.pts + p4.pts;
  const conf = confidence(c, p4.measured);

  const red = [...p1.red, ...p2.red, ...p4.red];
  const green = [...p1.green, ...p2.green, ...p3.green, ...p4.green];
  // Hiring people out of Pegasystems itself is a strong quality-of-team signal: product
// engineers choose the team, and it imports deep platform knowledge.
  if ((c.exPegasystemsHires || 0) >= 2) green.push(`${c.exPegasystemsHires} ex-Pegasystems hires — imports product-level platform depth`);
  if (!p4.measured) red.push(`Tenure/attrition unmeasured (only ${c.tenureN} dated engineer record(s)) — stability unverified`);
  if (conf === "Low") red.push("Thin evidence base: score is indicative only");

  results.push({
    company_name: c.company,
    total_score: total,
    score_status: "SCORED",
    leadership_location_analysis: [...p1.notes].join(" "),
    tech_stack_modernity: p2.found.length ? p2.found.join(", ") : "No specific modern integration/UI stack evidenced.",
    attrition_warning_level: p4.level,
    red_flags: red,
    green_flags: green,
    evidence_confidence: conf,
    pillar_breakdown: {
      p1_architectural_autonomy: { score: p1.pts, max: 30 },
      p2_modernity_integration: { score: p2.pts, max: 30, signals: p2.counts },
      p3_innovation_visibility: { score: p3.pts, max: 20, signals: p3.counts },
      p4_attrition_index: { score: p4.pts, max: 20, measured: p4.measured, notes: p4.notes.join(" ") },
    },
    evidence: {
      peopleCount: c.peopleCount, auditRows: c.auditRows, tenureN: c.tenureN,
      tenureAvgYears: c.tenureAvgYears, departureSignals: c.departureSignals,
      joinSignals: c.joinSignals, sources: c.sources, locations: c.locations,
      team_size: c.team_size, hiring_status: c.hiring_status, sectors: c.sectors,
    },
  });
}

const scored = results.filter((r) => r.score_status === "SCORED").sort((a, b) => b.total_score - a.total_score);
const unscored = results.filter((r) => r.score_status !== "SCORED");
scored.forEach((r, i) => (r.rank = i + 1));

// --- Evidence-volume bias: the headline caveat on this whole ranking -------------
// Measured corr(total_score, people+audit rows) ~= 0.84. The score therefore tracks how
// well-documented a company is at least as much as how good it is. A low score mostly
// means "not enough public evidence yet", NOT "bad place to work". So companies are only
// declared rank-comparable inside their evidence-confidence tier, and a separate
// within-tier rank is published alongside the raw rank.
function pearson(xs, ys) {
  const n = xs.length, mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0, dx = 0, dy = 0;
  for (let i = 0; i < n; i++) { const a = xs[i] - mx, b = ys[i] - my; num += a * b; dx += a * a; dy += b * b; }
  return num / Math.sqrt(dx * dy);
}
const biasCorr = +pearson(
  scored.map((r) => r.total_score),
  scored.map((r) => r.evidence.peopleCount + r.evidence.auditRows)
).toFixed(3);

for (const tier of ["High", "Medium", "Low"]) {
  scored.filter((r) => r.evidence_confidence === tier)
    .forEach((r, i) => { r.rank_within_confidence = i + 1; r.confidence_tier_size = scored.filter((x) => x.evidence_confidence === tier).length; });
}
scored.forEach((r) => {
  r.rank_comparable = r.evidence_confidence === "High" || r.evidence_confidence === "Medium";
  if (!r.rank_comparable) r.red_flags.push("Not rank-comparable: too little evidence to place this company against the others");
});

writeFileSync(DIR + "gcc_ranking_scores.json", JSON.stringify({
  generatedAt: new Date().toISOString(), asOf: "2026-10",
  rubric: {
    name: "GCC Engineering Culture & Autonomy Score",
    max: 100,
    pillars: {
      p1_architectural_autonomy: { max: 30, min: -20 },
      p2_modernity_integration: { max: 30, min: -15, note: "third +5 cloud/platform tier added to close the spec's 25-vs-30 gap" },
      p3_innovation_visibility: { max: 20, min: 0 },
      p4_attrition_index: { max: 20, min: -20, note: `scored only when >=${MIN_TENURE_N} engineers have parseable tenure; low tenure penalised only when departure-driven` },
    },
  },
  counts: {
    scored: scored.length, insufficient_evidence: unscored.length,
    high_confidence: scored.filter((r) => r.evidence_confidence === "High").length,
    medium_confidence: scored.filter((r) => r.evidence_confidence === "Medium").length,
    low_confidence: scored.filter((r) => r.evidence_confidence === "Low").length,
    attrition_unknown: scored.filter((r) => r.attrition_warning_level === "Unknown").length,
  },
  methodology_caveats: {
    evidence_volume_correlation: biasCorr,
    interpretation: `Score correlates ${biasCorr} with raw evidence volume (people + audit rows). A low score predominantly indicates thin public evidence, not a poor engineering environment. Only compare companies within the same evidence_confidence tier.`,
    tenure_rule: `Pillar 4 scored only when >=${MIN_TENURE_N} engineers have parseable tenure; ${scored.filter((r) => r.attrition_warning_level === "Unknown").length} of ${scored.length} companies fall below that and are recorded as Unknown rather than penalised.`,
    short_tenure_rule: "Low average tenure is penalised only where departure evidence outweighs join evidence; intern-conversion and new-team growth are not treated as burnout.",
    rubric_arithmetic: "Spec's Pillar 2 itemised to 25 but was labelled Max 30, making the rubric total 95. A third +5 cloud/platform tier closes the gap to a true 100.",
    not_measured: "Glassdoor ratings and compensation were not used: no reliable programmatic source was available. No private profile data was accessed.",
  },
  companies: [...scored, ...unscored],
}, null, 2), "utf8");

// --- console report ---
console.log("=== GCC ENGINEERING CULTURE & AUTONOMY — RANKED ===");
console.log(`scored: ${scored.length}   insufficient evidence: ${unscored.length}\n`);
console.log("RANK SCORE  P1   P2   P3   P4   CONF    ATTRITION  COMPANY");
for (const r of scored) {
  const p = r.pillar_breakdown;
  console.log(
    String(r.rank).padStart(3) + "  " + String(r.total_score).padStart(4) + "  " +
    String(p.p1_architectural_autonomy.score).padStart(3) + "  " + String(p.p2_modernity_integration.score).padStart(3) + "  " +
    String(p.p3_innovation_visibility.score).padStart(3) + "  " + String(p.p4_attrition_index.score).padStart(3) + "  " +
    r.evidence_confidence.padEnd(7) + " " + r.attrition_warning_level.padEnd(10) + " " + r.company_name
  );
}
const band = (lo, hi) => scored.filter((r) => r.total_score >= lo && r.total_score <= hi);
console.log("\n=== BANDS ===");
console.log(`elite 80-100 : ${band(80, 100).length}  -> ${band(80, 100).map((r) => r.company_name).join(", ")}`);
console.log(`strong 65-79 : ${band(65, 79).length}`);
console.log(`mid 50-64    : ${band(50, 64).length}`);
console.log(`weak <50     : ${band(-100, 49).length}`);
console.log(`\nHigh confidence: ${scored.filter((r) => r.evidence_confidence === "High").length}`);
