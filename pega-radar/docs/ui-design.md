# Pega Radar interface

Pega Radar is a personal search tool for a Pega developer targeting Bengaluru product companies and GCCs.
The interface helps the user find relevant roles, compare the work and expectations, keep a shortlist, and track applications.

## Visual direction

An open canvas, compact top navigation and clear typography give the work room to breathe. The palette combines
cool white, dark ink and cobalt. A small warm accent appears only in the source illustration. The app requires no
remote fonts, artwork, packages or frontend build.

First use has an asymmetric composition: the search brief and primary action on the left, a static source diagram
on the right. The diagram explains employer career sites, LinkedIn and India job boards. Its ready/searching state
reflects the current scan; it contains no invented jobs or vacancy totals. The brief uses the configured location,
certification and salary target, explicitly labeled as a target.

Once roles exist, the workspace presents a two-column collection of comparison cards. Each card contains employer,
title, location, experience, advertised salary, relevant evidence, source freshness, fit and actions. Missing salary
is stated explicitly. Experience stretches, stale listings and other cautions appear ahead of generic positives.
Full evidence remains available in the detail panel.

Desktop cards reserve two title lines for aligned decision fields. Long desktop titles use an ellipsis with their
full text available to assistive technology, on hover and in the detail panel. Single-column tablet and phone views
show the full title. Cards become a single column below 981px.

## Tokens

| Purpose | Light theme |
| --- | --- |
| Canvas | `#F7F9FC` |
| Surface | `#FFFFFF` |
| Primary text | `#17202B` |
| Supporting text | `#56667A` |
| Action cobalt | `#244BDB` |
| Source illustration field | `#E8EEF9` |

Dark theme values are defined separately in `web/app.css`. Amber denotes cautions or incomplete scans. Red denotes
failures. Helvetica Neue, Helvetica, Segoe UI and Arial provide local font fallbacks. Display type reaches 80px on
desktop; role titles are 21–24px. Numerals use tabular alignment where comparison matters.

## Interaction choices

- Primary role destinations and quieter coverage/source destinations share the top navigation.
- Global navigation counts stay separate from filtered result counts. Empty counts are hidden.
- Search and removable chips are immediately available. Location, employer and minimum-fit controls are grouped
  under Refine search, which closes on Escape or an outside click.
- First use foregrounds one scan action and a secondary coverage link. Empty search controls and export are hidden.
- Saved, Pipeline and Hidden keep separate filter preferences from discovery.
- Opening a role preserves keyboard navigation and restores focus on close. Native dialogs contain details.
- Notes retain a browser draft until the local server confirms saving.
- Bulk read affects only the unread roles loaded in the current list.
- Mobile navigation scrolls horizontally; the initial scan action remains visible without scrolling at tested sizes.

## Verification

Semantic theme colors, control boundaries, safe DOM rendering and interactions are covered by the offline tests.
The source illustration is static. Reduced-motion preferences disable remaining transitions and scan animations.
Browser checks cover both themes, phone/tablet/desktop layouts, filters, notes recovery, collection changes and
first use. See `ui-validation.md` and `ui-browser-report.json` for the latest results and limitations.
