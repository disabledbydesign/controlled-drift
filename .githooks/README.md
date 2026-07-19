# Git hooks

Enabled with `git config core.hooksPath .githooks` (already set in this clone; a FRESH clone must
run it once — git does not pick up a versioned hooks directory on its own).

## pre-commit

Enforces `docs/BUILD_DOC.md` §3 clause 5: if a commit changes how an Anytype property is written
or read, that field's entry in `scripts/field_semantics.py` travels in the SAME commit.

That clause is the one that keeps getting missed, and it fails quietly — nothing breaks, the tests
stay green, a review passes, and the semantics file drifts. It was missed on 99f577f (which added
a whole property) and surfaced only from a hand audit. §9 of BUILD_DOC exists "because
dispositions do not survive a session", which is why this is a hook and not a note.

Escape hatch, for a rename or a genuinely semantics-free touch:

    CD_SKIP_SEMANTICS_CHECK=1 git commit ...
