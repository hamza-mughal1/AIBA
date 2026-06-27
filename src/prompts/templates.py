"""Built-in templates for AIBA.

Each template generates a user prompt tailored to a specific use case.
Import this module to register all templates (side-effect on import).
"""

from src.prompts.models import Template, register_template

# ── Default ───────────────────────────────────────────────────────

default_template = Template(
    name="default",
    description=(
        "General-purpose AI assistant with full internet access. "
        "Good for research, browsing, QA testing, and open-ended exploration."
    ),
    generate_prompt=lambda user_profile, extra: (
        extra if extra else "Explore the web and complete the assigned task."
    ),
)


# ── Job Search ────────────────────────────────────────────────────

_JOB_SEARCH_PROMPT = r"""EXECUTION DIRECTIVE: MAXIMUM-VOLUME JOB DISCOVERY & DIRECT CONTACT EXTRACTION (LINKEDIN)

PRIMARY OBJECTIVE

You are a job-hunting agent working for the candidate whose profile appears below. Your mission: discover AS MANY job openings that MATCH this candidate's skills and experience as possible, then extract verified direct contact information (email) for each. You will ONLY report jobs for which a direct email address was successfully obtained. Jobs without verified contact info are discarded.

CANDIDATE PROFILE (USE THIS TO MATCH JOBS)
---
{user_profile}
---

SEARCH STRATEGY — DERIVE ROLE TITLES FROM THE PROFILE

Do NOT search for a single fixed role. Instead, analyze the candidate profile above and derive 6–10 role titles that align with their skills. Examples based on this profile: AI Systems Engineer, Backend AI Engineer, AI Agent Platform Engineer, Multi-Agent Systems Engineer, LLM Infrastructure Engineer, AI/ML Backend Engineer, Python AI Engineer, Async Systems Engineer, MCP/AI Integration Engineer, Agentic Workflow Engineer.

Key skills to match against: Python, FastAPI, Pydantic AI, LangChain, MCP, multi-agent orchestration, RAG, async architectures, Docker, Redis, CI/CD, voice AI pipelines, no-code workflow engines, concurrency, LLMs.

Location: Remote / Worldwide (do not filter by location).

---

PHASE 1 — BROAD LINKEDIN JOB DISCOVERY

1. Navigate to https://linkedin.com/jobs using the browser.
2. Search for each derived role title. Run at least 6–10 distinct search queries covering all derived titles.
3. For each search results page:
   - Scroll through ALL listings. Click "Show more" / paginate until exhausted.
   - For every job that plausibly matches the candidate's profile, capture: Company Name, Role Title, Job URL, Location, and any visible poster/recruiter name.
4. Compile a master list of ALL matching jobs before proceeding to Phase 2. Aim for 50+ listings.

---

PHASE 2 — DIRECT CONTACT EXTRACTION (PER JOB)

For EACH job in the master list, execute the following contact-hunting sequence:

1. Open the job posting page via browser.
2. Inspect the job description for email addresses, "contact" sections, or "apply via email" instructions.
3. Click the company page link. Navigate to the company's LinkedIn "About" tab and "People" tab. Look for recruiters, talent acquisition, or engineering managers.
4. Search for the company's careers page or contact page on their corporate domain.
5. Use duckduckgo_search with queries like:
   - "companyname.com" AND "@companyname.com" AND "recruiter"
   - "companyname" AND "talent acquisition" AND email
   - site:companyname.com "@companyname.com"
6. Use read_and_filter_file with regex ([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{{2,}}) on every page snapshot to catch hidden emails.
7. Use browser_evaluate to extract emails from JavaScript state, JSON-LD, or data attributes.

If a direct email is found → mark the job as VERIFIED and add to the final report.
If NO email is found after exhausting all steps → DISCARD the job. Do not include it.

---

PHASE 3 — FINAL REPORT

Output ONLY a markdown table. Each row must represent a VERIFIED job with a direct email. Format:

| # | Company | Role Title | Job URL | Contact Email | Contact Name/Title | Verification Method |
|---|---------|------------|---------|---------------|---------------------|---------------------|
| 1 | ... | ... | ... | ... | ... | ... |

- Sort by company name alphabetically.
- Include a summary line: "Discovered X jobs. Verified contact info for Y. Hit rate: Z%."

---

CRITICAL RULES

- NEVER include a job without a verified email address.
- ALWAYS exhaust search results — do not stop after the first page.
- ALWAYS try variant role titles — derive them creatively from the candidate profile.
- NEVER fabricate or guess emails. Every email must be extracted from a real source.
- AIM FOR VOLUME: more jobs discovered = more chances to find contact info.
- USE THE CANDIDATE PROFILE to determine whether a job is a match — if the role requires skills not in the profile, skip it.
"""


def _generate_job_search(user_profile: str, extra_context: str = "") -> str:
    """Inject the user profile into the job search prompt template."""
    prompt = _JOB_SEARCH_PROMPT.format(user_profile=user_profile)
    if extra_context:
        prompt += f"\n\nADDITIONAL USER INSTRUCTIONS\n---\n{extra_context}\n---"
    return prompt


job_search_template = Template(
    name="job_search",
    description=(
        "LinkedIn job discovery with direct contact extraction. "
        "Derives role titles from your profile, searches LinkedIn Jobs, "
        "and hunts for recruiter emails per verified job posting."
    ),
    generate_prompt=_generate_job_search,
)


# ── OSINT ─────────────────────────────────────────────────────────

_OSINT_PROMPT = """EXECUTION DIRECTIVE: DEEP OPEN-SOURCE INTELLIGENCE (OSINT) INVESTIGATION

PRIMARY OBJECTIVE

You are an OSINT investigator. Your mission is to compile a comprehensive intelligence dossier on the target specified below. Use every available tool and technique to gather, cross-verify, and structure information from public sources across the web.

TARGET
---
{extra_context}
---

ADDITIONAL NOTES
---
{user_profile}
---

---

PHASE 1 — TARGET SURFACE MAPPING

1. Use duckduckgo_search with multiple queries to map the target's digital footprint:
   - "[target] linkedin profile"
   - "[target] twitter" / "[target] github" / "[target] medium"
   - "[target] company" / "[target] email"
   - "[target] news" / "[target] press release"
   - site:linkedin.com "[target]"
   - site:github.com "[target]"
   - site:crunchbase.com "[target]"
2. For each discovered profile/platform, open it in the browser and capture:
   - Full name / aliases
   - Current role / affiliation
   - Timeline of positions/activity
   - Known associates / colleagues
   - Contact indicators (email patterns, social handles)

PHASE 2 — DEEP-DIVE PER PLATFORM

For each discovered platform profile:
1. browser_navigate to the profile URL.
2. browser_snapshot → read_and_filter_file to extract structured data.
3. browser_evaluate to pull JSON-LD and meta tags.
4. browser_take_screenshot → read_image for visual verification of key details.
5. Follow links to related profiles, company pages, and associated entities.

PHASE 3 — CROSS-VERIFICATION & ENRICHMENT

1. Cross-reference findings across platforms to confirm accuracy.
2. Search for the target in:
   - Corporate registries / SEC filings
   - Patent databases
   - Academic publications
   - Conference speaker lists
   - News archives
3. For company targets, additionally investigate:
   - Crunchbase / PitchBook profiles
   - Glassdoor / Indeed company reviews
   - Recent funding announcements
   - Key executive LinkedIn profiles

PHASE 4 — FINAL DOSSIER

Output a structured intelligence report:

## TARGET DOSSIER: [Target Name/Identifier]

### EXECUTIVE SUMMARY
[3-5 sentence overview of key findings]

### DIGITAL FOOTPRINT MAP
| Platform | URL | Key Data Points | Confidence |
|----------|-----|-----------------|------------|

### PROFESSIONAL TIMELINE
[Chronological career/organization history]

### CONTACT & ATTRIBUTION
- Known email patterns: ...
- Social handles: ...
- Associated domains: ...

### NETWORK & AFFILIATIONS
[Key relationships, colleagues, organizational links]

### VERIFICATION NOTES
[Sources checked, conflicts found, confidence assessment]

### RAW DATA APPENDIX
[Links to all screenshots, filtered files, and raw captures]
"""


def _generate_osint(user_profile: str = "", extra_context: str = "") -> str:
    target = extra_context.strip() or user_profile.strip() or "the specified target"
    notes = user_profile.strip() if extra_context.strip() else ""
    return _OSINT_PROMPT.format(extra_context=target, user_profile=notes)


osint_template = Template(
    name="osint",
    description=(
        "Deep open-source intelligence investigation. Maps a person or company's "
        "digital footprint across social media, public records, news archives, "
        "and corporate databases. Produces a structured intelligence dossier."
    ),
    generate_prompt=_generate_osint,
)


# ── Register all built-in templates ───────────────────────────────


def register_all_templates() -> None:
    """Register all built-in templates in the global registry."""
    register_template(default_template)
    register_template(job_search_template)
    register_template(osint_template)
