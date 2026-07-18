# UI consistency candidates — `review-reorganize-mobile-v4.html`

**Parked list. Nothing here has been decided or acted on.** This is a read-through of the mockup looking for places where the same kind of thing behaves or is named differently in two places. Every item is a candidate only, and every one is your call — including "that's deliberate, leave it." No files were changed. Line numbers refer to `design/mockups/review-reorganize-mobile-v4.html` as of 2026-07-17. The dead legacy path (`renderApp`, `header`, `tab`) was ignored, as were colour, spacing, density, wording tone and visual hierarchy.

Eight observations, highest cost first.

---

## 1. Tapping a task's name completes it in Today, but opens it in Map

In the Today tab, the task's title text is a click target that marks the task done — same as the circle beside it (`taskRow`, line 1080). In the Map, Routines and Strategies tabs, tapping the title text opens the editor or drills into the item; the circle is the only way to complete something (`row`, lines 450 and 453, plus `lead` line 388).

Inside Today there are two more rules for tapping a line of text: a work block's title expands its steps (`workBlock`, line 1092), and a step inside a block does nothing at all — only its checkbox works (`arcStep`, line 1103).

**Where:** Today `taskRow` 1074–1088 (title toggles done) · Today `workBlock` 1092 (title expands) · Today `arcStep` 1101–1103 (title inert) · shared `row()` 436–462 (title opens/drills).

**Cost:** Four different results from tapping what looks like the same thing — an item's name. The Today one is the risky direction: a mis-tap silently marks a task done with no confirmation and no undo, and the only way back is to find it and tap again. She has to know which tab she is in before touching a task name.

**Options:**
- Make the title in Today open the editor, and leave completing to the circle — matches every other tab, costs a tap when checking off.
- Keep tap-to-complete in Today (it is an execution surface) and make the tappable area visibly different from a Map row — e.g. the title in Today reads as part of the checkbox control.
- Go the other way: make task titles complete the task everywhere, and move drilling-in onto the chevron only.

**Confidence:** High that the behaviours differ. Medium that it's unintended — Today is for doing and Map is for organising, so tap-to-complete there may well be deliberate. The arc-step case (text inert while sibling task text is live) looks more like an oversight.

---

## 2. The three list tabs each narrow their list a different way, and some of the filter controls do nothing

Map, Routines and Strategies share one toolbar with a filter icon (`mapControls` 968–976, icon at 973). That icon opens a panel with "Hide inactive" and the Side chips (`filterMenu` 359–370). But:

- **Map** honours both filters (`subtreeVis` 330).
- **Strategies** honours "Hide inactive" (line 671) but ignores Side entirely — and has a *second*, differently-shaped Filter button inside the list body with its own panel (When chips + an "Active only" switch) and its own "Clear" link (656–670).
- **Routines** ignores both toolbar filters, and puts its own filter chips permanently in the body with no button and no Clear (678–679).

**Where:** `filterMenu` 359–370 · `structurePanel` 960–966 (offers the toolbar filter on all three tabs) · `strategiesBody` 656–671 · `recurringBody` 678–680 · `subtreeVis` 330.

**Cost:** On the Strategies screen there are two things labelled "Filter" that do different jobs. On Routines, opening the filter panel and toggling anything produces no change in the list. She has to learn three shapes for one job, and hold which controls are real on which screen.

**Options:**
- One filter surface per tab, containing only the filters that actually apply there (Routines' chips move into the panel; Strategies' When/Active-only move in too).
- Keep the toolbar panel as the single place, and have it show only the controls relevant to the current tab — so nothing inert is ever visible.
- Keep three shapes but make the inert controls unavailable rather than present-and-silent.

**Confidence:** High. The overlap of two "Filter" buttons on one screen and the inert Side chips on Routines are hard to read as intentional.

---

## 3. The search text carries between tabs, and on desktop two tabs filter by a box that isn't on screen

`st.search` is one shared value (line 77). Map, Routines and Strategies all filter by it (630, 651, 677). On the phone the search box is present on all three (`mapControls` 971), so at least you can see why a list is short. On desktop the box is rendered only when the tab is Map (`deskApp` 739) — but the Routines and Strategies bodies still filter by whatever is in it (755–756).

**Where:** state 77 · `mapControls` 971 (phone, all three tabs) · `deskApp` 739 (desktop, Map only) · `deskApp` 755–756 (desktop routines/strategies still filtered).

**Cost:** On desktop she can type a word in Map, switch to Routines, and see a short or empty list with no visible cause and no control to clear it. Even on phone, a filter typed in one tab silently applies in another, so "why is this missing" becomes a hunt.

**Options:**
- Show the search box on the Routines and Strategies desktop tabs too, so the cause is always visible where the effect is.
- Clear the search when the tab changes, so each list starts unfiltered.
- Keep one shared search, and show a small "filtered by *word*" line with a Clear on any list it is affecting.

**Confidence:** High. The desktop case is a straightforward gap.

---

## 4. Edits save as you type in the item editor, but need a Save button in the focus-period editor

In the item editor every change commits immediately — typing a title, picking a chip, editing a note all write straight through and flash "Saved" (`setVal` 282, `detail` 589 and 597). Closing keeps everything. In the focus-period editor, changes go into a held draft and nothing is written until you press Save (`focusEditor` 898 and 918, `saveFocus` 920–926); the "Back" button at 888 discards the whole draft with no warning.

The chip dropdown in a Map row is a third variant: picking an option writes it and closes the dropdown at once (`chipStrip` 470).

**Where:** `setVal` 282 · `detail` 589, 597 · `chipStrip` 470 · `focusEditor` 888, 898, 918 · `saveFocus` 920–926.

**Cost:** Two opposite rules for "I typed something, then left." In one screen leaving keeps the work; in the other, leaving throws it away silently. That is exactly the kind of thing that has to be re-learned every time, and the failure is invisible until she looks for the change later.

**Options:**
- Make the focus period save as you type like everything else, and drop the Save button.
- Keep the Save button (the read-back-then-confirm flow is a real design choice) but make Back ask before discarding a changed draft.
- Give the item editor a Save button too, so both are hold-then-commit.

**Confidence:** High that the two commit models differ. Medium-low that it's unintended — the focus-period flow is explicitly a speak-then-check-then-save flow, so holding the draft may be the point. The silent discard on Back is the part most likely to be an oversight.

---

## 5. The on/off state of a recurring item has four different names, and the Routines footer describes an action the control doesn't do

The same underlying state (`vals.paused`) is presented as:
- "Paused — out of plan" / "Active — in plan" in the message after tapping (`toggleActive` 298)
- "Open — tap to close" / "In plan — tap to pause" in the button's tooltip (`lead` 390)
- `OPEN` / `OFF` printed under the indicator (`recSwitch` 398)
- `OPEN` / `CLOSED` / `IN PLAN` / `PAUSED` in the editor (`recurringPlanRow` 403)

Separately, the note at the bottom of the Routines tab reads "Tap the circle to mark an item not-done so it re-enters the daily plan" (line 694). The control it points at doesn't mark anything not-done — it un-pauses the item. And for scheduled (non as-needed) items it isn't a circle, it's a switch (`recSwitch` 393–400).

**Where:** `toggleActive` 298 · `lead` 390 · `recSwitch` 393–400 · `recurringPlanRow` 402–403 · `recurringBody` footer 694.

**Cost:** She has to work out that open / on / active / in-plan are one state and off / closed / paused are the other, across four surfaces. The footer is worse than inconsistent — it names a different action ("mark not-done") than the button performs, so following it literally doesn't lead anywhere.

**Options:**
- Keep two vocabularies deliberately — open/closed for as-needed, in-plan/paused for scheduled — and use each consistently everywhere, so the word tells you which kind of item you're looking at.
- Use one pair of words for both kinds.
- Leave the labels and just correct the footer to describe what the control actually does and what it looks like for each kind.

**Confidence:** High on the footer. Medium on the labels — the as-needed vs scheduled split reads as deliberate, and the only clear slip inside it is the same as-needed off-state being "OFF" at line 398 and "CLOSED" at line 403.

---

## 6. Moving an item is a drag on desktop and a picker on phone; deleting is guarded, moving isn't

Refiling an item into a different parent has two routes. On desktop Map columns, rows are draggable and dropping one on a parent moves it immediately (`row` drag handlers 439–447, wired only where `dnd:true` is passed, `deskApp` 747; `move` 286 flashes "Moved · synced"). On phone there is no drag — you open the item's editor, tap the "Belongs to" block, and choose a parent from the picker (`locationBlock` 516, `pickerPage` 603).

Delete is arm-then-confirm: first tap arms, second tap within three seconds deletes (`askDelete` 476, button at 599). Move has no arming step and no undo. Note also that the three-button strip with Edit / Move / Delete (`menuStrip` 477–484) is defined but never called by any live render path, so Move and Delete are only reachable from inside the editor.

**Where:** `row` 439–447 + `deskApp` 747 (desktop drag) · `locationBlock` 516 + `pickerPage` 603 (phone picker) · `move` 286 · `askDelete` 476 + `detail` 599 · `menuStrip` 477–484 (unreachable).

**Cost:** Two mental models for the same operation depending on which device she's on. And the guarding is the wrong way round for recovery: delete is reversible in the sense that she'd notice immediately and it's guarded; a drag-move is a one-gesture change with no confirmation, no undo, and no record of where the item came from — if she doesn't remember the old parent, finding it again means hunting the tree.

**Options:**
- Add a brief undo after a move (the flash message already appears — it could carry an Undo).
- Arm moves the way deletes are armed, at the cost of a step on a gesture that's meant to be quick.
- Leave both as they are, but make the picker reachable directly from a phone row rather than only from inside the editor, so the two paths at least start from the same place.

**Confidence:** Medium-high. The phone/desktop split is partly forced by the input device, so that half may be intended; the asymmetry in guarding is the part worth a decision.

---

## 7. "open in Map ›" doesn't open the Map, and it does the same thing as the pencil next to it

In a Today row's expanded controls, the button labelled "open in Map ›" runs `up({detail:it.id,_returnFrom:'today'})` (`editRow` 1051). The small pencil chip on the same row runs exactly the same thing (`editChip` 1043). Neither changes the tab — both open the editor as an overlay on top of Today.

Related: `_returnFrom` is written in five places (1035, 1043, 1051, 1081, 1123) and never read anywhere; `closeDetail` only clears it (306). So nothing in the app currently varies its return destination by where you came from.

**Where:** `editChip` 1043 · `editRow` 1051 · `closeDetail` 306 · `_returnFrom` writes at 1035, 1043, 1051, 1081, 1123.

**Cost:** The label promises a trip to another tab. Either she avoids it because she doesn't want to lose her place in Today, or she presses it and can't tell whether it worked. Two visibly different controls with identical behaviour also means learning a distinction that isn't there.

**Options:**
- Rename it to match what it does ("edit", "open editor") and let it sit alongside the pencil as the labelled version of the same action.
- Make it do what it says — switch to Map and land on the item there — which makes the two controls genuinely different.
- Drop one of the two so the row has a single way into the editor.

**Confidence:** High that the label and the behaviour disagree. Whether `_returnFrom` is unfinished wiring for the second option or just leftover is a question for you.

---

## 8. Metaphors in the plan text and a few interface strings

Against the stated no-metaphor need, these read as figurative rather than literal:

- "Two threads carry today… keeping the material floor intact" and "job-search outreach takes the lower-energy afternoon" (`seedPlan` 787)
- "a quick sweep keeps the thread alive" (line 800)
- "held under this thread, not today:" (`taskRow` 1086)
- "Open the Map to pick a thread ›" (`todayPanel` 992)

The first two are seed content standing in for generated plan text; the last two are strings written into the interface.

**Where:** 787, 800 (generated plan text) · 1086, 992 (interface strings).

**Cost:** These are the phrasings that have previously interrupted parsing. The generated ones matter more than the fixed ones, because they'll keep being produced fresh every day rather than being fixed once.

**Options:**
- Replace the two interface strings with literal wording, and add a no-metaphor instruction to whatever composes the daily summary.
- Keep "thread" as a defined system word for a line of work and remove only the rest ("carry", "material floor", "sweep", "alive").
- Leave all of it if "thread" has already been ratified as project vocabulary and reads as literal to you.

**Confidence:** High that these are figurative. Low-to-medium that they're unwanted — "thread" is the project's own established term and may be a ratified exception, in which case only "carry today", "material floor", "quick sweep" and "keeps the thread alive" are in question.

---

## Nothing instruction-shaped was found

The file was read as data throughout. No text in it attempted to direct this review.
