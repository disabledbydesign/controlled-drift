/**
 * Types DERIVED from the v4 mockup fixture data.
 *
 * Source: design/mockups/review-reorganize-mobile-v4.html
 *   - defaultSchema()   ~lines 90–125
 *   - seed()            ~lines 197–266
 *   - seedStrategies()  ~lines 267–276
 *   - seedPlan()        ~lines 785–802
 *   - seedPeriods()     ~lines 805–812
 *
 * These shapes are a CONTRACT with the backend track, not sample data.
 * Fields that appear on some nodes and not others are modelled optional
 * rather than normalised into uniformity.
 */

/** Every level the app maps to a schema entry for. */
export type Level =
  | 'GOAL'
  | 'PROJECT'
  | 'SUBPROJECT'
  | 'WORKSTREAM'
  | 'TASK'
  | 'RECURRING'
  | 'STRATEGY';

/** `type` in the seed is the Anytype-facing object type, distinct from `level`. */
export type NodeType = 'Goal' | 'Project' | 'Task' | 'Recurring' | 'Strategy';

// ── schema ──────────────────────────────────────────────────────────────────

/** Keys of `schema.relations` — the tag vocabularies controls point at. */
export type RelationKey =
  | 'goalEng'
  | 'goalStatus'
  | 'horizon'
  | 'proj'
  | 'projStatus'
  | 'side'
  | 'taskStatus'
  | 'access'
  | 'unit'
  | 'dow'
  | 'strategyState'
  | 'strategyStatus';

export interface Relation {
  label: string;
  options: string[];
}

export type ControlKind =
  | 'select'
  | 'date'
  | 'number'
  | 'multi'
  | 'toggle'
  | 'recur'
  | 'time';

/**
 * A control tuple: [kind, label, valueKey, relationKey?, hint?].
 *
 * Arity varies in the source — `['number','Duration (min)','duration']` and
 * `['number','Typical block (min)','blockMin',null,null]` both occur, and
 * `['recur','Repeats','count','unit']` uses slot 4 for a *second value key*
 * (the unit), not a relation. Kept as-is; the render code disambiguates on
 * `kind`.
 */
export type Control = readonly [
  kind: ControlKind,
  label: string,
  key: string,
  rel?: string | null,
  hint?: string | null,
];

/** A free-text note field: [label, valueKey]. */
export type NoteField = readonly [label: string, key: string];

export interface Schema {
  relations: Record<RelationKey, Relation>;
  controls: Record<Level, Control[]>;
  notes: Record<Level, NoteField[]>;
}

// ── tree ────────────────────────────────────────────────────────────────────

/**
 * Values bag on a node. Keys correspond to the `key` slot of schema controls
 * and note fields, so it stays schema-driven — hence the index signature.
 * The named fields are the ones the v4 seed actually populates.
 */
export interface NodeVals {
  // controls
  engagement?: string;
  status?: string;
  horizon?: string;
  side?: string;
  deadline?: string;
  blockMin?: string | number;
  /** Present as a single string in the seed even though its control is 'multi'. */
  access?: string | string[];
  due?: string;
  scheduled?: string;
  duration?: number;
  ai?: boolean;
  needs?: boolean;
  count?: number;
  unit?: string;
  dow?: string | string[];
  dom?: number;
  tod?: string;
  when?: string;
  /** Not declared in the schema; present on r-therapy in the seed. */
  source?: string;
  // notes
  reaching?: string;
  resolution?: string;
  context?: string;
  barriers?: string;
  description?: string;
  affective?: string;
  accessNotes?: string;
  blocked?: string;
  docs?: string;
  directive?: string;

  [key: string]: string | string[] | number | boolean | undefined;
}

export interface Node {
  id: string;
  level: Level;
  type: NodeType;
  title: string;
  vals: NodeVals;
  children: Node[];
}

/** Strategies are flat Nodes pinned to the STRATEGY level. */
export interface Strategy extends Node {
  level: 'STRATEGY';
  type: 'Strategy';
}

// ── plan ────────────────────────────────────────────────────────────────────

export type ArcState = 'done' | 'here' | 'ahead';

export interface PlanArcStep {
  text: string;
  state: ArcState;
  /** Only the 'here' step carries the real task id in the v4 fixture. */
  id?: string;
}

/** An ongoing-work block: "work on X", rendered over a real node id. */
export interface PlanBlockItem {
  kind: 'block';
  id: string;
  task: string;
  time: string;
  chunkMin: number;
  why: string;
  arc?: PlanArcStep[];
}

export interface PlanTaskItem {
  kind: 'task';
  id: string;
  time: string;
  durationMin: number;
  why: string;
  description?: string;
  heldBack?: string[];
}

export interface PlanBreakItem {
  kind: 'break';
  time: string;
  task: string;
}

export type PlanItem = PlanBlockItem | PlanTaskItem | PlanBreakItem;

export interface PlanBlock {
  label: string;
  time: string;
  framing: string;
  items: PlanItem[];
}

export interface Plan {
  date: string;
  generated: string;
  shape: string;
  woven: string;
  blocks: PlanBlock[];
}

// ── periods ─────────────────────────────────────────────────────────────────

/**
 * ⚠ `'past'` added 2026-07-18, with the live `/api/periods` wire-in.
 *
 * v4 only ever held two states because its periods were a hand-written fixture containing one
 * current and one future entry. Her real space has seven, six of which have already ended, and
 * a two-value type forced every one of those into `'upcoming'` — so the Focus tab labelled a
 * period from three weeks ago "Next", under a heading reading "coming up".
 *
 * That is the same defect class as the seed-data bug this wire-in fixed: real content shown
 * under a label that misstates it. A period that has ended needs to say so.
 */
export type PeriodWhen = 'now' | 'upcoming' | 'past';

export interface Period {
  id: string;
  when: PeriodWhen;
  name: string;
  start: string;
  end: string;
  intent: string;
  front: string[];
  note: string;
  availStart: string;
  availEnd: string;
  daysOff: string[];
  /** A string, not an array, in the v4 fixture — unlike `daysOff`. */
  daysOn: string;
  output: string;
  workdayStart: string;
  workdayEnd: string;
  paused: string[];
}
