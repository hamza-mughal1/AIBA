# Templates

A template is a pre-built mission brief. It defines the objective, the strategy, and the expected output — combined with your mode and effort, it determines AIBA's entire behavior.

You pick a template at launch (Step 2). AIBA takes your extra context from (Step 4), and injects them into the template. The result is a detailed, structured prompt that becomes the agent's marching orders.

Three templates ship out of the box. Each built for a different class of work.

---

## Available Templates

### `default`

General-purpose. No pre-defined strategy. What you type in Step 4 is exactly what the agent receives.

Good for research, browsing, QA testing, open-ended exploration — anything where you know what you want and don't need a structured playbook.

**Output:** Whatever the agent produces. No fixed format.

---

### `job_search`

Job discovery with direct contact extraction. Built for one purpose: find jobs that match your skills, then hunt down recruiter emails for each one.

**What it does:**

1. Analyzes your `USER_PROFILE` and derives 6–10 role titles from your skills
2. Searches job sites e.g. **LinkedIn Jobs** and **Indeed** for each title, exhaustively — every page, every listing

!!! warning
    It is recommended to share your browser session in `.playwright-mcp/cookies.json` in order for sites like **LinkedIn Jobs** and **Indeed** to allow the agent without facing a sign-in page. Learn more about browser sessions and cookies (covered in How-To Guides).

3. For each matching job, runs a contact-hunting sequence: inspects the posting, visits the company page, searches for recruiter emails across the corporate domain
4. Discards jobs without verified contact info. Only confirmed matches make the report.

**Inputs that matter:** `USER_PROFILE` is required to be set in `.env` for `job_search` template to work at its full potential, else it will only have the context given in the _extra context_ prompt (step 4).

**Output:** A markdown table of verified jobs with company, role, URL, contact email, contact name, and verification method. Sorted alphabetically by company.

---

### `osint`

Deep open-source intelligence investigation. Maps a person or company's digital footprint across the open web and produces a structured dossier.

**What it does:**

1. **Surface mapping** — discovers the target's presence across LinkedIn, Twitter, GitHub, Crunchbase, and news sources
2. **Deep-dive per platform** — opens each profile, captures structured data, screenshots, and meta tags
3. **Cross-verification** — checks findings against corporate registries, patent databases, academic publications, and news archives
4. **Dossier output** — compiles everything into a structured intelligence report

**Inputs that matter:** Extra context (Step 4) is the investigation target. `USER_PROFILE` is included as supplementary notes.

**Output:** A full dossier with executive summary, digital footprint map, professional timeline, contact & attribution, network & affiliations, and raw data appendix.

---

## Inputs at a Glance

| Template | Uses `USER_PROFILE`? | Uses extra context? |
|---|---|---|
| `default` | No | Yes — passed verbatim as the prompt |
| `job_search` | Yes — drives role derivation and job matching | Yes — appended as additional instructions |
| `osint` | Yes — included as supplementary notes | Yes — becomes the investigation target |

---

## How to Choose

Pick **`default`** when:

- You know exactly what you want and just need an agent to go do it
- You're exploring, researching, or QA testing
- You want a conversational REPL session

Pick **`job_search`** when:

- You're job hunting and want verified contact emails, not just links
- Your `USER_PROFILE` is filled in with your skills and experience
- You want volume — the template pushes for 50+ listings

Pick **`osint`** when:

- You're investigating a person, company, or organization
- You need a structured, cross-verified dossier — not a summary
- You want breadth — the template maps presence across multiple platforms

---

## Building Your Own

Templates are Python dataclasses with a `generate_prompt` function. You can register your own in `src/prompts/templates.py`.