# Attribution

This skill takes ideas from prior work and says which, because a skill about falsifiable claims
should not make an unfalsifiable one about its own originality.

## From `mcarlssen/claude-adversarial-review` (MIT)

https://github.com/mcarlssen/claude-adversarial-review

Three ideas were taken more or less whole, and they are the best ideas in that skill:

1. **A finding survives only if a skeptic cannot refute it.** Candidate findings are attacked before
   they are reported, rather than filtered by the reviewer's own confidence.
2. **Refute the negatives, not only the positives** — re-attack every all-clear using a *different
   search modality* than the one that produced it. This is the single highest-yield rule in either
   skill, and it is theirs.
3. **`risk = severity × confidence`** with reachability adjustments, including the distinction
   between *latent* (cannot run) and *env/data-gated* (runs; manifestation depends on an operational
   fact), and scoring inert infrastructure at would-be-reachable weight.

That skill in turn vendors its over-engineering lens from `DietrichGebert/ponytail-review` (MIT).

## What this skill adds

The additions come from defects that shipped in a real trading codebase, each of which passed review
and a green test suite:

- **The claim taxonomy** — six kinds of claim, only the first of which ordinary review attacks.
- **Sabotage verification** (§4) — a guard is not a guard until it has been *seen* to fail. Break the
  guarded thing, run the test, and if it still passes the test is decorative. Three such tests were
  found in one codebase, each *pinning* the bug it existed to catch.
- **Decorative guards** (§3c) — a check whose failing branch no caller can reach because every caller
  passes a constant. Found on an execution path as `assertCanSubmit({ released: true })`, which read
  as a hard guardrail while being a literal.
- **Unfalsifiable claims** (§3d) — a sign, unit, direction or timezone with no convention stated
  where it is declared. Nothing can be wrong, so nothing can be caught. Found as a hedge-direction
  inversion that had shipped for the life of the file.
- **Empirical reachability** (§5) — "did a row appear", not "could this run". A module with complete
  passing tests and zero production rows is a finding, usually the largest available.
- **Silent success** (§5) — anything reporting success while its side effect did not happen. One such
  pipeline ran dead for ten days behind a page that looked healthy.
- **Budget and output discipline** (§0) — findings first, emitted incrementally, and a run that ends
  with no verdict counts as FAIL rather than clean. Added because an adversarial agent in that
  codebase twice burned its whole turn budget exploring and returned only preamble. `[reported]`
- **"Not checked" names which kind of gap it is** (§7) — budget, or an instruction that could not be
  followed. Added 2026-09-21. `[measured: 2/4 → 6/6]`, see `MEASUREMENTS.md`.
- **A one-reader fallback** (§0) — run the lenses and skeptics yourself when you cannot dispatch
  agents, and say so. Added 2026-09-24 from a reader audit of this file. `[untested]`
- **"Underpowered" as a refutation** (§3) of the audit's own finding. Added 2026-09-24. `[untested]`
- **A parsable last line with an UNMEASURED slot** (§7), read by `scripts/check_report.py`. Added
  2026-09-24. `[untested]` for its effect on readers; the checker itself has a self-test.
- **Cumulative messages ending `FALSIFY_PARTIAL:`** (§0) when running as a sub-agent, because only a
  sub-agent's final message reaches its caller. Added 2026-09-24 from the sibling `supervision`
  skill's record of turn-limit halts. `[untested]`
- **Two measurement claim rows and a §3e**, proposed 2026-09-24 and withdrawn the same day after a
  null blind-reader test. `[measured: null]`, see `MEASUREMENTS.md`. The trading-specific checks
  that motivated them live in `tradingview-backtesting` §13.

### Tags

Each addition above carries one tag, so a reader can tell evidence from belief about this skill's
own rules:

- `[measured: …]` — a blind-reader comparison with and without the rule was run; the number and the
  write-up are in `MEASUREMENTS.md`.
- `[reported]` — the failure that motivated the rule was observed; the rule's effect was not measured.
- `[untested]` — neither. The same tag appears next to the rule inside `SKILL.md`.

`check-falsify.sh` at the repository root reports which of these additions a copied `SKILL.md`
carries, so an installed copy that has drifted behind this one is visible.

## Scope difference

`claude-adversarial-review` reviews an uncommitted diff. `falsify` audits claims, which includes
diffs but also whole-repo questions a diff cannot express: is this test able to fail, has this code
path ever executed, does this convention exist.

MIT, like its parents.
