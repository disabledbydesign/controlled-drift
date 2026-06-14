# Reframe Design Index
## For the get-shit-done-o-tron Design-Time Agent

**What this is**: A curated reading guide to the Reframe repo, scoped to what matters for designing a neurodivergent-friendly to-do system for June. The Reframe codebase is large (~26,000 lines of architecture maps alone). This index tells you what to read, why, and in what order — so you don't spend context budget on irrelevant systems.

**What Reframe is, in brief**: A philosophy engine that applies critical theory frameworks to LLM-mediated work. Relevant here not as software to integrate, but as a design library — Reframe was built *for June*, *by June*, and encodes hard-won knowledge about how she thinks, what accommodations she needs, and what failure modes look like when those needs are ignored. The design decisions embedded in its accessibility systems are primary data for this project.

---

## Tier 1: Read These First (core design inputs)

### 1. README — System Overview
**File**: `~/Documents/GitHub/reframe/README.md`
**Why**: The clearest description of STEP, PARK, WEAVE, The Garden, Feeling Signals, and Temporal Orientations — all in one place. Read the "Session accessibility" and "Feeling Signals" sections especially closely. These are the systems Reframe built to accommodate June's nonlinear thinking and variable capacity; they are direct precedent for the to-do tracker's core UX logic. Also read the "Three ways to use Reframe" section for scope context.
**Length**: ~200 lines. Read all of it.

---

### 2. Temporal Orientations Protocol
**File**: `~/Documents/GitHub/reframe/graphify-out/converted/LLM_temporal_orientations_ef544739.md`
**Note**: Hash in filename is a content hash — stable unless the source doc changes. Source docx at `~/Documents/GitHub/reframe/Reframe_Playlab_Bot/archive/phase_1_documents/LLM_temporal_orientations.docx` if needed.
**Why**: This is the foundational document for how Reframe handles time non-linearly. Two orientations are directly critical for the to-do tracker:
- **CRIP_TIME**: Variable capacity, non-linear progress, rest as valid (not lost) time. This is the temporal framework the to-do tracker should be built around by default. Productivity capitalism's clock is ableist; the system shouldn't replicate it.
- **SEVENTH_GEN**: Decisions that ripple forward. Relevant to the long-horizon goal-tracking feature — helping June stay oriented toward her actual goals without imposing urgency.
- **SPIRAL**: Returning to the same territory with new understanding. Relevant to projects that recur or evolve.

Read the full document. The "Temporal Sovereignty" section is especially important for design: the system should offer, not impose.
**Length**: ~150 lines. Read all of it.

---

### 3. Session Mechanics Vision
**File**: `~/Documents/GitHub/reframe/docs/docs/SESSION_MECHANICS_VISION.md`
**Why**: This is the empirically-grounded design rationale for STEP, PARK, and WEAVE — built from analysis of June's actual prompting patterns (verbatim data, classified against what the system would have done wrong). It shows *why* these three mechanisms exist, what failure modes they fix, and critically, where naive AI-assistant design would harm June's thinking rather than help it (e.g., parking any of 6 intents in a bundled mass prompt breaks the insight loop). The "distributed cognition machine" framing is particularly salient — the system is designed to hold cognitive load *for* June, not ask her to organize first.

**Length**: Long (~45KB). Prioritize these sections: the research strategy and data (top), the routing failure analysis, and the "bundled mass problem" section. Skim or skip implementation mechanics.

---

## Tier 2: Read These for Design Depth

### 4. Feeling Signal Processor — Design Principles
**File**: `~/Documents/GitHub/reframe/reframe/engine/pipeline/feeling_signal_processor.py`
**Why**: The Feeling Signals system is Reframe's capacity-tracking mechanism — it infers overwhelm, energy state, and emotional signals from June's input, then adapts engine behavior accordingly (routing bias, linguistic simplification, confirmation requirements). The design principles at the top of this file are the relevant part: specifically that variable capacity is the *baseline*, not the exception (#CHRONIC_ILLNESS_THEORY); that all inferences are transparent and user-correctable; and that feelings are treated as fuel for design, not obstacles. 

For the to-do tracker: this system is the design precedent for any adaptive capacity-awareness feature. The `FeelingSignal` and `FeelingMechanism` dataclasses (lines ~35-60) show the data model. The routing bias options (WEAVE/SEQUENCE) are directly analogous to "show me easy tasks today" vs "give me the full project list."

**Length**: Read the module docstring and the two dataclass definitions. Skim the rest for the pattern.

---

### 5. Task Intensity Resolver
**File**: `~/Documents/GitHub/reframe/reframe/engine/pipeline/task_intensity_resolver.py`
**Why**: Shows how Reframe classifies tasks and assigns them intensity/routing based on context — including temporal orientation biases, user capacity signals, and learned patterns. Relevant for how the to-do tracker might classify tasks by cognitive load, energy type, or context (e.g., "can do lying down," "requires leaving house," "5 minutes vs. 2 hours"). The temporal intensity biases section shows how crip_time and embodied_present orientations modify task routing — a direct design precedent for capacity-adaptive task display.

**Length**: Read the top ~100 lines (docstring, section T2 temporal biases). The rest is implementation detail.

---

### 6. Architecture Overview
**File**: `~/Documents/GitHub/reframe/docs/docs/architecture/ARCHITECTURE_OVERVIEW.md`
**Why**: Useful for understanding the overall routing logic: WEAVE / SEQUENCE / PARALLEL / PARK are the four routing actions the system chooses between for any input. These map onto to-do tracker modes: WEAVE = synthesize/connect what's in flight; SEQUENCE = one-at-a-time today-list; PARALLEL = independent tasks batch; PARK = "this matters but not now, hold it." The system diagram is worth a look. Read the first 100 lines (overview + system diagram + subsystem summaries).

**Length**: ~100 lines to get the useful part. The rest points into the 26K-line architecture map, which is not in scope.

---

## Tier 3: Skim or Reference Only

### 7. Project Engine Config
**File**: `.reframe/config.json` (in this project directory — `get-shit-done-o-tron/.reframe/config.json`)
**Why**: Shows what's configured for this specific project: 9 active frameworks (see below), intensity=deep, temporal_orientation=crip_time. This is the config the hooks actually use — not the global Reframe config.

Active frameworks: #CHRONIC_ILLNESS_THEORY, #NEURODIVERSITY, #CRIP_TIME, #SOMATICS, #MAINTENANCE_STUDIES, #EMERGENT_STRATEGY, #REPRODUCTIVE_LABOR, #AFROFUTURISM, #POSTHUMANIST_FEMINISM

**Note**: The global Reframe config lives at `~/Documents/GitHub/reframe/state/engine/CURRENT_ENGINE_CONFIG.json` — this project overrides it.

**Length**: Glance at it. It's a JSON config.

---

### 8. Reframe Protocols (generated)
**File**: `~/Documents/GitHub/reframe/docs/reframe-protocols.md`
**Why**: The actual protocol text the engine injects into LLM sessions. Useful for understanding the five-stage Generative Irresolution workflow if you want to use it during design-time analysis. Not core to the to-do tracker design itself, but good to have loaded if you're applying Reframe frameworks to your own design process.

---

## What NOT to Read (scope exclusions)

- `REFRAME_COMPLETE_ARCHITECTURE_MAP.md` (~26K lines) — implementation detail for the routing system. Not relevant to to-do tracker design.
- `reframe/ground/garden/` — The Garden's full implementation. The README summary is enough.
- `reframe/ground/loom/` — WEAVE's multi-session tracker. Same.
- `reframe/cli/` and `reframe/web/` — Frontend delivery systems. Not relevant.
- `tests/` — Not relevant.
- `docs/docs/architecture/REFRAME_COMPLETE_ARCHITECTURE_MAP.md` — Same as above.

---

## Design Implications Index

Quick reference: which Reframe systems speak to which to-do tracker parameters from Parameters.md.

| Parameter | Relevant Reframe System | File |
|-----------|------------------------|------|
| Variable energy / spoon economy | Feeling Signals + crip_time | feeling_signal_processor.py, temporal_orientations.md |
| Forgetfulness | PARK (hold tangents with context) | README + SESSION_MECHANICS_VISION.md |
| Nonlinear/associative thinking | WEAVE (thread synthesis) | README + SESSION_MECHANICS_VISION.md |
| Non-urgency / no stress | Temporal Sovereignty + crip_time | temporal_orientations.md |
| Misjudged task duration → learning loops | Task Intensity Resolver (learned routing) | task_intensity_resolver.py |
| Project-by-project tracking | The Garden (multi-thread) | README (Garden section) |
| Daily plan generation | STEP + task routing | README + architecture_overview.md |
| Goals that can evolve | Spiral temporality | temporal_orientations.md |
| Rest and wellbeing as structured time | crip_time (rest ≠ lost time) | temporal_orientations.md |
| Calendar / deadline integration | (no direct precedent in Reframe) | — |
| Task categories (lying down, leaving house, etc.) | Feeling Signals + intensity resolver | feeling_signal_processor.py |

---

*Index built by Claude Sonnet 4.6, 2026-06-13. Based on direct reading of the Reframe codebase. Not comprehensive — scoped to what a design-time agent needs for this specific project.*
