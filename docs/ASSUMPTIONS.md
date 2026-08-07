# Financial and policy assumptions

All outcomes below are deterministic simulations in Indian rupees (INR). Source
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
- Expected-loss ceiling: PD × LGD no greater than 12% of EAD.
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
