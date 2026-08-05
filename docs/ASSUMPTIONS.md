# Financial and policy assumptions

All outcomes below are deterministic simulations in Taiwan dollars (TWD).

- LGD: 65%. Loss share of EAD after default; not estimated from UCI.
- Credit conversion factor: 75%. Applied to positive undrawn line.
- Interchange rate: 1.8% of simulated incremental annual spend.
- APR: 18% applied to the simulated revolving share.
- Revolving rate: 45% of simulated incremental spend.
- Funding cost: 4.5% of incremental EAD.
- Capital cost: 2.5% of incremental EAD, separate from expected loss.
- Servicing cost: TWD 60 for an increase action.
- Response elasticity: 35% of incremental line × observed utilization per month,
  annualized over 12 periods. It is not a causal estimate.
- Maximum automatic increase: 30%.
- Maximum account exposure: TWD 1,000,000 proposed line.
- Portfolio growth cap: 10% over current aggregate line.
- Expected-loss ceiling: PD × LGD no greater than 12% of EAD.
- Profitability hurdle: TWD 100 simulated annual incremental contribution.

The simulator validates every rate in [0, 1] and requires non-negative monetary
controls. Sensitivity should focus on LGD/CCF, response elasticity, APR,
funding/capital costs, loss ceiling and hurdle. No assumption should be promoted
to production without empirical estimation, governance approval and monitoring.

