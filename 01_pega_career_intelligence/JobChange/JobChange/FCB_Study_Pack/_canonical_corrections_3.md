# Canonical Corrections, part 3 — authored by lead

Restores the Reg CC availability numbers that were correctly deleted in batch 1 for want of a
source. These are now sourced. **APPLY VERBATIM** into `ch12_deposits_banking_domain.html`,
immediately after the calendar block from Part 3 (§12.10), before the Reg E worked examples.

All figures verified 2026-10-12 against the current eCFR text of 12 CFR 229.10 and 229.12.
The dollar amounts reflect the inflation adjustment published at 89 FR 43738/43739 (20 May 2024),
effective **1 July 2025**. These amounts are adjusted for inflation every five years — state the
effective date whenever quoting them.

---

```html
    <h3>Reg CC funds availability — the schedule, with citations</h3>
    <p>Availability is where the two Reg CC calendars collide in a single sentence, and the
      regulation is precise about it: funds are available "not later than the <strong>business
      day</strong> after the <strong>banking day</strong> on which the deposit is made." The banking
      day fixes <em>when the deposit counts as made</em>; business days are what you then count
      forward. Get those the wrong way round and every date in the schedule shifts.</p>

    <h4>Next-day availability — 12 CFR 229.10</h4>
    <table>
      <tr><th>Deposit type</th><th>Available</th><th>Conditions</th><th>Cite</th></tr>
      <tr><td>Cash, deposited in person to a bank employee</td><td>Business day after the banking day of deposit</td><td>—</td><td>229.10(a)(1)</td></tr>
      <tr><td>Cash, <em>not</em> in person</td><td>Second business day</td><td>—</td><td>229.10(a)(2)</td></tr>
      <tr><td>Electronic payments (wire, ACH credit)</td><td>Business day after the banking day the bank <em>received</em> it</td><td>"Received" means actually and finally collected funds <em>and</em> the account/amount information — both</td><td>229.10(b)</td></tr>
      <tr><td>US Treasury check</td><td>Business day after the banking day of deposit</td><td>Deposited into an account held by a payee</td><td>229.10(c)(1)(i)</td></tr>
      <tr><td>Cashier's, certified or teller's check</td><td>Business day after</td><td>Payee's account, <strong>in person</strong>, and on a special deposit slip if the bank requires one</td><td>229.10(c)(1)(v)</td></tr>
      <tr><td>State / local government check</td><td>Business day after</td><td>Payee's account, in person, depositary bank in the issuing state, special slip if required</td><td>229.10(c)(1)(iv)</td></tr>
      <tr><td>On-us check (same bank, same state or check-processing region)</td><td>Business day after</td><td>—</td><td>229.10(c)(1)(vi)</td></tr>
      <tr><td><strong>The first <span class="tag">$275</span> of a day's other check deposits</strong></td><td>Business day after</td><td>The lesser of $275 or the aggregate deposited that banking day by checks not already covered above</td><td>229.10(c)(1)(vii)</td></tr>
      <tr><td>Those same checks when <em>not</em> deposited in person</td><td>Second business day</td><td>Applies to (ii)–(v) above</td><td>229.10(c)(2)</td></tr>
    </table>

    <h4>The availability schedule — 12 CFR 229.12</h4>
    <table>
      <tr><th>Deposit type</th><th>Available</th><th>Cite</th></tr>
      <tr><td>Local checks</td><td>Second business day following the banking day of deposit</td><td>229.12(b)</td></tr>
      <tr><td>Nonlocal checks</td><td>Fifth business day</td><td>229.12(c)(1)</td></tr>
      <tr><td>Deposits at a <strong>nonproprietary</strong> ATM (cash or check)</td><td>Fifth business day</td><td>229.12(f)</td></tr>
      <tr><td>Alaska, Hawaii, Puerto Rico, Guam, American Samoa, N. Mariana Is., US Virgin Is.</td><td>May extend the above by one business day, for checks drawn on a paying bank outside the state</td><td>229.12(e)</td></tr>
      <tr><td>Withdrawal by cash or similar means</td><td>May extend by one business day — <strong>but</strong> $550 must be available for cash withdrawal by <strong>5:00 p.m.</strong> on the day the funds are otherwise available, <em>in addition to</em> the $275 under 229.10(c)(1)(vii)</td><td>229.12(d)</td></tr>
    </table>

    <div class="note"><strong>Two details that mark out someone who has read the regulation rather
      than a summary of it.</strong>
    <ul>
      <li><strong>The $550 is additive, not a replacement.</strong> §229.12(d) says so explicitly:
        it "is in addition to the $275 available under §229.10(c)(1)(vii)". Most summaries get this
        wrong, and the 5:00 p.m. clock on it is a hard time-of-day obligation, not a day count.</li>
      <li><strong>The local/nonlocal split is largely historical.</strong> The Federal Reserve
        consolidated check processing into a single region, so in practice virtually every check
        now meets the "local" definition and falls under the second-business-day schedule; the
        nonlocal five-day schedule in §229.12(c) survives in the text but rarely bites. Worth saying
        out loud — it shows you know why the regulation reads the way it does.
        <span class="tag amber">structural point, not a quoted figure — confirm before relying on it operationally</span></li>
    </ul></div>

    <div class="warning"><strong>The dollar amounts move.</strong> $275 and $550 come from the
      inflation adjustment at 89 FR 43738 and 43739 (20 May 2024), <strong>effective 1 July
      2025</strong>, replacing the previous $225 and $450. Reg CC amounts are adjusted on a
      five-year cycle. Never quote them without the effective date, and never hard-code them —
      they belong in configuration with an effective-dated history, exactly like the deadline
      records in the table above. An interviewer who knows this regulation will be listening for
      whether you attach a date to the number.</div>

    <div class="note"><strong>Exception holds are a separate mechanism.</strong> The schedules above
      are the default. Reg CC separately permits longer holds in defined circumstances — new
      accounts, large deposits, redeposited checks, repeated overdrafts, reasonable cause to doubt
      collectibility, and emergency conditions — each with its own notice requirements. Those
      thresholds are also inflation-adjusted. This chapter does not quote them; look them up at
      §229.13 with the current effective date before using any figure.
      <span class="tag amber">not quoted here — look up §229.13 before use</span></div>
```

---

## Also apply

In the same chapter, make sure the ACH row of the Part 3 calendar table does **not** say "Federal
Reserve holidays" (batch 1 already changed this to the network/operator calendar — confirm it held).

Add these three rows to ch12's Part 0.3 references table:

| Source | URL | Release / effective date | Supports |
|---|---|---|---|
| 12 CFR 229.10 (eCFR, current) | https://www.ecfr.gov/current/title-12/chapter-II/subchapter-A/part-229/subpart-B/section-229.10 | Amounts effective 1 Jul 2025 (89 FR 43738) | Next-day availability categories; the $275 aggregate; in-person conditions; electronic-payment receipt test |
| 12 CFR 229.12 (eCFR, current) | https://www.ecfr.gov/current/title-12/chapter-II/subchapter-A/part-229/subpart-B/section-229.12 | Amounts effective 1 Jul 2025 (89 FR 43739) | Local/nonlocal schedules; nonproprietary ATM; the $550 cash-withdrawal floor and its 5:00 p.m. deadline |
| 89 FR 43738 (inflation adjustment) | https://www.federalregister.gov/citation/89-FR-43738 | Published 20 May 2024, effective 1 Jul 2025 | That $225→$275 and $450→$550 took effect 1 Jul 2025, and that the amounts adjust every five years |
