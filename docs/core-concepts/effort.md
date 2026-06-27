# Effort

Effort controls how hard AIBA pushes. You pick it at launch (Step 3) — it determines the model's behavior, the resource budget, and the depth of investigation. Same mode, same template. Three different intensities.

---

### There are three effort levels in AIBA: [quick](#quick), [balanced](#balanced), and [max](#max)

---

## quick

Fast. Cheap. Shallow. Built for answers you need in seconds, not minutes.

The agent uses minimal tool calls, skips pagination, and avoids the browser unless a page absolutely requires it. One or two sources are enough — get the answer and move on.

In swarm mode, the orchestrator plans 1–2 waves max, then synthesizes immediately. No looping. No chasing leads.

**Best for:** Quick lookups. Fact-checking. "What is X?" questions. Testing a prompt before running it deeper.

---

## balanced

Thorough but pragmatic. The daily driver.

The agent cross-checks facts across 2–3 sources, uses the browser for dynamic content, and paginates where it matters — but doesn't exhaust every page. It delivers structured, well-organized results without burning through your quota.

In swarm mode, the orchestrator plans 2–3 waves. After wave 2 it asks: "Do I have enough to answer well?" If yes, it synthesizes. No chasing diminishing returns.

**Best for:** Most things. Research tasks. Multi-source verification. The default you'll use 80% of the time.

---

## max

Exhaustive. Every tool. Every page. Every lead.

The agent leaves no stone unturned. It stacks browser navigation with visual screenshots, JavaScript evaluation, multi-hop navigation, and full pagination exhaustion. It cross-verifies across every available source. In `max` mode only, Gemini gets extra reasoning compute — it *thinks harder* before acting.

In swarm mode, the orchestrator plans 4–8 waves across multiple vectors. It chases pivot leads recursively. After wave 5 it shifts toward synthesis to ensure a deliverable ships before the budget runs out.

**Best for:** Deep-dive investigations. Competitive analysis. OSINT dossiers. Anything where completeness matters more than cost.

---

## What Effort Changes

| Dimension | quick | balanced | max |
|---|---|---|---|
| **Temperature** | 0.3 (deterministic) | 0.5 (flexible) | 0.7 (creative) |
| **Max tokens / response** | 4,096 | 8,192 | 16,384 |
| **Request limit** | 15 | 25 | 50 |
| **Tool call limit** | 20 | 40 | 100 |
| **Total token budget** | 100K | 300K | 500K |
| **Timeout** | 30s | 60s | 120s |
| **Thinking (Gemini)** | Off | Off | High |

---

## Effort Across Modes

Effort applies to both execution modes, but it means something slightly different in each.

**In Agent mode:** The sub-agent receives behavioral instructions matching your effort — concise for quick, thorough for balanced, exhaustive for max.

**In Swarm mode:** Both layers get effort-specific guidance. The orchestrator gets wave-planning instructions (1–2, 2–3, or 4–8 waves). Every spawned sub-agent gets matching depth instructions (minimal tools, cross-check, or full arsenal).

Same effort, same budget — applied to every agent in the system.

---

## How to Choose

Pick **quick** when:

- You need a fast answer — fact, date, definition
- You're testing a prompt before committing more resources
- Token cost matters

Pick **balanced** when:

- You're doing real research — not just a lookup
- You want cross-verified results without overkill
- You're running `job_search` for a focused search

Pick **max** when:

- Completeness is non-negotiable
- You're running `osint` or a deep competitive analysis
- The task branches — each finding opens new leads
- You're running in swarm mode and want full pivot detection
