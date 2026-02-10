# Specs Conventions

Deze map bevat technische/productspecs voor niet-triviale wijzigingen.

## Wanneer een spec maken

Maak een spec als een wijziging:

- publieke API's of contractgedrag verandert;
- DB-schema, indexen of migratiepad raakt;
- security- of validatiegedrag wijzigt;
- meerdere lagen raakt (API + DB + UI + tests).

Voor kleine, lokale refactors of pure typo-fixes is geen spec nodig.

## Lifecycle

Elke spec heeft een `Status`:

- `Proposed`: idee/ontwerp, nog niet gebouwd.
- `Accepted`: scope en aanpak zijn beslist.
- `Implemented`: code staat in repo en is gevalideerd.
- `Superseded`: vervangen door een nieuwere spec.

Werk na implementatie de spec altijd bij met:

- implementatiedatum;
- commit/PR referenties;
- korte verificatie-evidence (tests + security checks).

## Scope-afbakening

- `AGENTS.md`: proces, kwaliteitsgates en securityregels (hoe we werken).
- `specs/`: beslissingen en afbakening van features (wat/waarom).

Dupliceer geen volledige testscript-inhoud in specs; verwijs naar echte tests in `audit-api/tests/`.

## Naamgeving

- Gebruik oplopende prefixen: `001-...`, `002-...`, ...
- Hou titels taakgericht en eenduidig.
