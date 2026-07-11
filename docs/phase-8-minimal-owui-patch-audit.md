# Phase 8 minimal Open WebUI patch audit

Recorded on 2026-07-11 against upstream Open WebUI `v0.10.2` at
`ecd48e2f718220a6400ecf49eafd4867a38feb10` and the maintained
`rebaseline/upstream-v0.10.2` branch at `6dca01731`.

## Outcome

The maintained Open WebUI branch contains one retained custom feature: the
feature-flagged native Welcome UI island. Flows and Media are in Studio,
timeline persistence remains parked for Studio, and the remaining custom
features are either replaced by upstream or excluded from the maintained
fork.

The user parked Pi Gateway. The immutable legacy source remains the sole
reference; Phase 8 includes no extraction, port, or upstream contribution.

## Baseline and patch series

The maintained branch descends from the exact v0.10.2 tag. Its
ordered patch history is:

1. `559cd28f1` - add the disabled-by-default Welcome seam and catalogue tests;
2. `e9ca2fc11` - restore the full Welcome presentation using v0.10.2 APIs;
3. `3ccdbe83c` - harden ordering and composer/file handoff and add `PATCHES.md`;
4. `da39eb4a1` - separate sidebar New Chat from the parameter-free Welcome route;
5. `6dca01731` - update the patch register only.

`PATCHES.md` records the purpose, ownership boundaries, configuration, file
surface, verification, rebase procedure, and rollback for the retained
feature. An operator can set `ENABLE_WELCOME_PAGE=False` to restore upstream
home-route behaviour without a database or storage conversion.

## Actual retained surface

The complete delta from v0.10.2 is ten files: the patch register, two backend
configuration lines, one typed frontend configuration field, the home-route
selection, the isolated Welcome component and catalogue tests, a bounded Chat
attachment handoff, and the sidebar route distinction.

The integration hook stays small even though the self-contained Welcome
presentation is substantial. It adds no database table, migration,
backend domain model, API router, background job, provider credential,
package dependency, or static branding asset. OWUI continues to own users,
permissions, models, functions, files, and chats.

The source diff has no `package.json`, `static`, backend model, or backend
router change. `git diff --check v0.10.2..HEAD` passes.

## Branding and navigation

No custom branding or static asset is retained. The only navigation delta is
the removable Welcome seam:

- parameter-free `/` shows Welcome only when `ENABLE_WELCOME_PAGE=True`;
- query-bearing `/` routes continue to the upstream Chat component;
- sidebar New Chat uses `/?new=true`, while the logo and product name retain
  the parameter-free Welcome route.

This keeps navigation configuration-driven and leaves Studio directly
addressable at `/studio`; no Studio domain logic is added to OWUI.

## Pi Gateway and experiments

The maintained branch has no Pi Gateway component, route, configuration,
model, router, seed, package delta, or static asset. The
exact upstream v0.10.2 tag includes the `@mediapipe/tasks-vision` dependency
visible in `package.json`; this patch series leaves it unchanged.

The current plan includes no move or extraction. A future Pi Gateway proposal
needs its own scope and must start from the immutable legacy source. Do not
restore it as part of another OWUI change.

## MCP and generally useful fixes

The maintained branch contains no custom MCP or OAuth patch. Upstream v0.10.2
already covers the retained token-authentication, callback, timeout, and
cleanup requirements identified in the comparison.

The unique-suffix tool-name resolver remains conditional. Reproduce the
exact-name failure with an intended
staging model first; if it blocks required MCP use, prepare a narrow upstream
contribution with exact, unique, ambiguous, and unknown-name tests. Otherwise
the maintained patch set remains unchanged.

## Verification evidence

- The team recorded four passing Welcome catalogue/order/query assertions
  under Node 22.
- The team built the full v0.10.2 Vite frontend with the retained series.
- The local deployment passed health, native chat handoff, file
  attachment, dictation, voice, ordering, quick actions, and distinct Welcome
  and New Chat navigation checks.
- The user completed the authenticated Flow canvas confidence checklist on
  2026-07-11; this changes no OWUI patch surface but closes the remaining
  Phase 7 manual confidence check.

The current machine-wide Node 24 npm shim is broken. This audit relies on the
recorded Node 22 evidence and changes no application source.

## Exit gate assessment

1. The only retained OWUI feature is single-purpose, disabled by default,
   documented, tested, and isolated behind a small configuration/routing hook.
2. Large domain products do not live in the maintained OWUI fork: Flows and
   Media are Studio-owned, timeline persistence is parked for Studio, and Pi
   Gateway remains legacy-only.
3. The patch series is already applied as an ordered, reviewable history on
   the exact clean v0.10.2 tag, with a documented rebase and removal procedure.

The recorded evidence satisfies Phase 8 for v0.10.2. Provider-specific MCP
testing remains staging work. Add an upstream contribution or retained patch
only after reproducing the blocker.
