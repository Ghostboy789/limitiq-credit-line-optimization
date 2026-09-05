# Financial and policy assumptions

## Current v4 evidence and currency boundary

The primary model output is a Taiwan-source probability of default in the
following month. It is not an Indian-market, regulatory or IFRS 9 PD. The
expected-loss display is an educational proxy: `score × LGD × EAD`.

V4 operates on 1,200 deterministic synthetic six-month histories matching the
behavioral primary contract. Limits, balances and economics are generated in
INR; the USD/EUR control is presentation-only. No source customer, causal line
response, realized profit or Indian borrower outcome is represented.
Synthetic annual income is derived deterministically from line and payment
history; synthetic monthly obligations are generated from an identifier-indexed
FOIR schedule. FOIR is `total_monthly_obligation_inr / (income_inr / 12)`.
Credit-line count and credit age are also deterministic synthetic fields.
Profiles above the 60% FOIR safeguard route to manual review. These fields match
the semantics of the India readiness contract, but they are not observed,
verified or representative Indian ability-to-pay data.


The v4 base policy assumes LGD 65%, base CCF 75%, PD-linked CCF sensitivity
50%, interchange 1.8%, APR 18%, revolving rate 45%, funding cost 4.5%, capital
cost 2.5%, servicing cost ₹180 and response elasticity 35%. Response to an
increase is multiplied by `exp(-2.5 × increase_pct)`; the dimensionless decay
`kappa=2.5` is an assumption, not an estimated treatment effect. Effective CCF
is `min(75% + 50% × score, 100%)`, also an assumption. Policy controls assume
maximum increase 30%, maximum account exposure ₹3,000,000, portfolio growth cap
10%, portfolio loss-growth cap 8%, capital allocation rate 8%, portfolio capital
budget ₹25,000,000, higher-risk increase share 25%, expected-loss-rate ceiling
`score × LGD <= 12%`, and profitability hurdle ₹300. Every value is adjustable
simulation input, not an approved production policy or estimate.

## Historical v2 evidence and currency boundary

The model probability is a source-specific adverse-outcome estimate, not a
common-horizon PD. The expected-loss display is therefore an educational proxy:
`adverse-outcome probability × LGD × EAD`, not IFRS 9 ECL or regulatory capital.

Only source-disclosed currencies are localized to INR. V2 uses 2.97 INR/TWD and
83 INR/USD as fixed presentation rates. Give Me Some Credit and Home Credit
currencies are undisclosed; their monetary values are not converted or shown as
INR. South German DEM amounts are not used as INR income/exposure fields.

The v2 app operates on 1,200 deterministic synthetic profiles. Current limits,
balances, economics, actions and financial outcomes are synthetic—not copied
source rows, causal forecasts or realized impact.

The v2 base policy uses LGD 65%, CCF 75%, interchange 1.8%, APR 18%, revolving
rate 45%, funding cost 4.5%, capital cost 2.5%, servicing cost ₹180, response
elasticity 35%, maximum increase 30%, maximum account exposure ₹3,000,000,
portfolio growth cap 10%, expected-loss ceiling 12% and profitability hurdle
₹300. All remain adjustable educational assumptions.

## Verified v1 assumptions

All v1 outcomes below are deterministic simulations in Indian rupees (INR). Source
monetary fields are converted at a fixed 2.97 INR/TWD. This is a presentation
transform, not Indian borrower evidence or a live exchange-rate commitment.

- LGD: 65%. Loss share of EAD after default; not estimated from UCI.
- Credit conversion factor: 75%. Applied to positive undrawn line.
- Interchange rate: 1.8% of simulated incremental annual spend.
- APR: 18% applied to the simulated revolving share.
- Revolving rate: 45% of simulated incremental spend.
- Funding cost: 4.5% of incremental EAD.
- Capital cost: 2.5% of incremental EAD, separate from expected loss.
- Servicing cost: ₹180 for an increase action.
- Response elasticity: 35% of incremental line × observed utilization per month,
  annualized over 12 periods. It is not a causal estimate.
- Maximum automatic increase: 30%.
- Maximum account exposure: ₹3,000,000 proposed line.
- Portfolio growth cap: 10% over current aggregate line.
- Expected-loss-rate ceiling: PD × LGD no greater than 12%; EAD is not part of this account check.
- Profitability hurdle: ₹300 simulated annual incremental contribution.

The simulator validates every rate in [0, 1] and requires non-negative monetary
controls. Sensitivity should focus on LGD/CCF, response elasticity, APR,
funding/capital costs, loss ceiling and hurdle. No assumption should be promoted
to production without empirical estimation, governance approval and monitoring.

The rate is the rounded July 2026 USD cross-rate: RBI 24 July 2026 reference
rate 96.5390 INR/USD divided by Bank of Taiwan 31 July 2026 closing spot
32.4800 TWD/USD = 2.97226, rounded to 2.97. Sources:
https://m.rbi.org.in/Scripts/BS_ViewBulletin.aspx?Id=22920 and
https://rate.bot.com.tw/cr?Lang=en-US.
