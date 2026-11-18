# UI validation

Pega Radar's UI runs against the existing local Python server. Its runtime still
needs only Python's standard library; the frontend has no install or build step.
Development and validation must not request job boards or employer websites.

## Completed browser review

On 15 November 2026, 77 browser checks passed in local Chrome 157.0.8103.51 on macOS,
with no uncaught page errors. The browser exercised the real local Python API with
12 synthetic roles and a separate unseeded database.

Both themes were checked at 1440 × 1040, 834 × 1112, 390 × 844 and 320 × 800.
New roles, Saved, Pipeline, Employer coverage and Scan sources had no page-level
horizontal overflow at those sizes. All roles, Hidden, the mobile detail panel,
keyboard navigation, note recovery, collection updates and filter errors
were exercised separately.

The scan button and progress state were checked with intercepted responses.
No real scan, job-board request or employer-site request was made. Reduced-motion
behavior and the first-scan action's visibility on a phone were also checked.
The Refine search disclosure was exercised through its actual location controls,
Escape dismissal with focus restoration, and outside-click dismissal.
Firefox, Safari, physical touch devices and screen readers have not been tested.

The individual checks are recorded in [ui-browser-report.json](ui-browser-report.json).
Preview images:

- [Desktop with synthetic roles](ui-desktop.png)
- [Mobile with synthetic roles](ui-mobile.png)
- [Dark theme with synthetic roles](ui-dark.png)
- [First use on desktop](ui-first-run.png)
- [First use on mobile](ui-first-run-mobile.png)

The previews containing roles show fictional test data, not live vacancies.

## Automated checks

From the `pega-radar` directory:

```sh
python -B -m unittest discover -s tests
```

The suite contains 551 tests. The frontend behavior test also needs an existing
Node installation and is skipped if Node is unavailable. It uses a fake DOM,
timers, local storage and HTTP responses; it does not start a browser or contact
job sites.

The UI checks cover:

- Global navigation counts and keyboard focus after navigation updates.
- The configured first-use brief, coverage entry point and scan progress transition.
- Salary disclosure and prioritization of cautions without losing full role evidence.
- Independent discovery, Saved, Pipeline and Hidden filter settings.
- Loading feedback, failed-filter recovery and removal of stale results.
- Saving, hiding, restoring and changes to collection membership.
- Durable note drafts, reload recovery and retry after failed saves.
- Marking only loaded unread roles as read, including partial save failures.
- Scan modes, incomplete sources, coverage gaps and unsafe external text.
- Light and dark theme contrast, local assets and safe DOM construction.

A passing fake-DOM test does not prove browser layout, native dialog behavior,
screen-reader output or touch interaction. Those require browser review.

## Synthetic browser fixture

`tests/ui_fixture.py` creates 12 fictional roles in a new, empty temporary folder.
It refuses non-temporary destinations and existing data. It never starts scans
or makes network requests. The fixture is not automatically loaded by the app.

For macOS or Linux:

```sh
python -B -m tests.ui_fixture /tmp/pega-radar-ui-review
PEGA_RADAR_DATA=/tmp/pega-radar-ui-review python -B radar.py serve --no-browser
```

For Windows Command Prompt:

```bat
python -B -m tests.ui_fixture "%TEMP%\pega-radar-ui-review"
set "PEGA_RADAR_DATA=%TEMP%\pega-radar-ui-review"
python -B radar.py serve --no-browser
```

Open the loopback address printed by the server. Use a different empty temporary
folder for each fresh fixture. All displayed employers, jobs and recorded scan
outcomes in this fixture are synthetic. Do not trigger a real scan while reviewing
the fixture.

The data includes Bengaluru and other locations; product, GCC, services and other
employer types; saved, applied, interviewing, offer, rejected and hidden states;
salary and experience variants; long and untrusted text; a missing description;
and an incomplete-source warning.

## Browser review checklist

- At desktop and mobile widths, inspect New roles, All roles, Saved, Pipeline,
  Hidden, Employer coverage and Scan sources.
- Confirm the page has no unintended horizontal overflow, and that long role
  titles and employer names remain readable.
- Open a role, use Tab and Escape, and check focus when the drawer closes.
- Save and unsave a role; change an application status; hide and restore a role.
- Edit a note, reload, reopen the role and confirm the note remains.
- Narrow discovery filters, then open Saved and Pipeline to confirm their
  independent defaults expose roles elsewhere.
- Open roles and use the bulk-read action; check that its count tracks the
  loaded unread roles and that roles outside the filters remain unread.
- Inspect the loading, first-use, no-match and disconnected states using isolated
  data or mocked responses.
- Check both themes, visible keyboard focus and reduced-motion preferences.
- Confirm no console errors, unintended external requests or live job-site calls.

Record the browser, viewport sizes and actual outcomes with the review artifacts.
This checklist describes required scenarios; it is not itself a claim that every
browser scenario has passed.
