# Dataset attribution, provenance and publication status

LimitIQ code is MIT licensed. That licence does not grant rights to third-party
datasets or override upstream, competition or mirror terms. Raw datasets are
gitignored and must never be committed.

## Publication gate — owner resolution attestation (14 Aug 2026)

On 14 August 2026 the repository owner explicitly confirmed that the publication
rights issue identified below was resolved and directed the project to proceed.
The supporting legal or contractual documents are retained by the owner and are
not included here; this is an owner attestation, not an independent legal opinion
by the project or its automated contributors.

The source notes below preserve the earlier 11 August research findings for
auditability. They describe what the project itself could establish from public
pages before the owner supplied the resolution attestation.

## Historical review decision (12 Aug 2026)

The four sources below were documented as blocked pending a human terms review
(see the log). This section preserves that earlier evidence and decision trail;
the later 14 August owner resolution attestation above is the current project
gate status.

The earlier review did not independently establish terms for:

1. Give Me Some Credit original Kaggle competition terms.
2. FICO/HELOC custom challenge terms and the Kaggle-to-OpenML cleaning chain.
3. Lending Club upstream rights despite the CodeSignal mirror's CC0 declaration.
4. Home Credit competition and unofficial mirror terms.

This is a redistribution/derived-artifact gate. It does not authorize publication
merely because the files are downloadable or the project is educational.

## Terms-review log

| Source | Reviewed URL / document | Review date | Redistribution finding | Trained artifact publishable? |
|---|---|---|---|---|
| Give Me Some Credit | Kaggle Terms of Use §8 (`https://www.kaggle.com/terms`) | 11 Aug 2026 | Competition data is licensed for "the sole purpose and duration of the Competition"; the OpenML "Public" flag is platform metadata, not a licence. No upstream waiver located. | Not established — keep local |
| FICO/HELOC | FICO XML Challenge notice (`https://investors.fico.com/news-releases/news-release-details/fico-announces-xml-challenge/`) | 11 Aug 2026 | OpenML licence metadata says `Unknown (Kaggle) / Custom (FICO website)`. No permissive FICO terms located. | Not established — keep local |
| Lending Club | CodeSignal HF mirror CC0 declaration (`https://huggingface.co/datasets/codesignal/lending-club-loan-accepted`) | 11 Aug 2026 | Mirror declares CC0-1.0, but upstream Lending Club platform terms were not located to confirm they permit the mirror grant. | Not established — keep local |
| Home Credit | Unofficial HF mirror (`https://huggingface.co/cantalapiedra/poc_scoring_fair`) | 11 Aug 2026 | Unofficial mirror, no compatible licence established; original competition terms require review. | Not established — keep local |

The mirror declarations are recorded as platform metadata, not as independent
evidence that clears upstream redistribution rights. The project publication
decision relies on the later owner attestation; an institution must perform its
own source-terms review before using or redistributing these artifacts.

## V1 primary dataset

**Default of Credit Card Clients**, created by I-Cheng Yeh and distributed by
the UCI Machine Learning Repository:

- Source: https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients
- DOI: https://doi.org/10.24432/C55S3H
- Licence: CC BY 4.0
- Population/time: 30,000 Taiwan accounts; April–September 2005 behavior;
  subsequent-month default label
- Raw SHA-256:
  `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933`

The repository does not redistribute the raw XLS. The v1 demonstration uses
deterministic synthetic account identifiers and excludes original identifiers
and demographics.

## V2 source ledger

### Corrected South German Credit — training

- Source: https://archive.ics.uci.edu/dataset/573/south+german+credit+update
- DOI: https://doi.org/10.24432/C5QG88
- Licence: CC BY 4.0
- Population/time: 1,000 South German credits, 1973–1975; 700 good / 300 bad;
  bad credits were oversampled
- Label: whether the contract was complied with; horizon undisclosed
- Raw SHA-256:
  `5f363343f356ca38a0236baab849e472846399b2176ccc5bd686483dd8a7562f`

### Legacy Statlog German Credit — reference only

- Source: https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data
- DOI: https://doi.org/10.24432/C5NC77
- Licence: CC BY 4.0
- Raw SHA-256:
  `b21f3d81db8071257d5ff1deaeba1fd4303b62712e6fcc9715c7a86202cb5871`

UCI describes corrected South German as a correction of this same underlying
1,000-credit population. Statlog is therefore excluded from training and row
budgets to prevent duplicate-population leakage; it is not a seventh independent
market.

### Give Me Some Credit — historical terms concern

- Origin: Kaggle Give Me Some Credit competition
- Immediate mirror: OpenML dataset 45577 / file 22116561
- Metadata: https://www.openml.org/api/v1/json/data/45577
- Download mirror: https://api.openml.org/data/download/22116561/dataset
- Rows used: 150,000 competition-training records
- Label: serious delinquency within two years
- Geography/currency/collection period: undisclosed
- Mirror metadata: `Public`, which is not a standard open licence; original
  competition terms apply
- Raw SHA-256:
  `1d1a66d10042a3ff8ed4f7712f52c2701ccef1924509cc11420188f512af327a`

No Give Me Some Credit monetary field is presented as INR because the source
currency is not established.

### FICO Explainable ML / HELOC — historical terms concern

- Origin: FICO Explainable Machine Learning Challenge
- Origin notice:
  https://investors.fico.com/news-releases/news-release-details/fico-announces-xml-challenge/
- Immediate mirror: cleaned OpenML dataset 45554 / file 22116522
- Metadata: https://www.openml.org/api/v1/json/data/45554
- Download mirror: https://api.openml.org/data/download/22116522/dataset
- Upstream/mirror rows: 10,459 / 9,871; the mirror removed records containing
  only the `-9` sentinel and encoded `-9/-8/-7` as missing
- Label: `RiskPerformance=Bad`; exact horizon undisclosed in the immediate mirror
- Geography/collection period: undisclosed; no monetary feature is localized
- Licence metadata: `Unknown (Kaggle) / Custom (FICO website)`
- Raw SHA-256:
  `e2598f0b585e19a67eadc545ddfc659122b654be74c791e91c21a998404f0bcd`

### Lending Club accepted loans — historical terms concern

- Immediate mirror:
  https://huggingface.co/datasets/codesignal/lending-club-loan-accepted
- File:
  https://huggingface.co/datasets/codesignal/lending-club-loan-accepted/blob/main/accepted_2007_to_2018Q4.csv
- Mirror file commit:
  `6f83c7b49a39b1d3c15b0598d730336438127821`
- Raw/harmonized rows: 2,260,701 / 1,371,166
- Population/time/currency: US accepted loans issued 2007–2018Q4; USD
- Label: status at extract—Fully Paid versus Charged Off, Default or Late;
  variable horizon; Current/In Grace and other statuses are excluded
- Mirror declaration: CC0-1.0; upstream Lending Club rights were not
  independently verified, so the mirror claim is recorded separately and does
  not independently clear publication. Release relies on the owner attestation
  recorded above
- Raw SHA-256:
  `3eae03c28fd9d2e8a076ebeb73507e8d4d0f44d90500decdb0936e0933d1f36a`

### Home Credit application data — historical terms concern

- Origin: Home Credit Default Risk competition
- Immediate unofficial mirror:
  https://huggingface.co/cantalapiedra/poc_scoring_fair/blob/main/application_train.csv
- Mirror file commit:
  `283af2554979fcb5513d2e50c59542b705e7abf6`
- Rows: 307,511
- Label: payment difficulty; X-day delinquency within Y days, with X, Y and the
  resulting horizon undisclosed
- Geography/currency/collection period: undisclosed
- Licence: the public-page review did not establish a compatible mirror licence
  and flagged the original competition terms. Release relies on the owner
  attestation recorded above
- Raw SHA-256:
  `52e96b895b1112e1c853f670e58372719c8441c5ed1c57ac2f7fad559d784f5f`

Home Credit monetary fields are not converted or represented as INR.

## Separate validation datasets

The existing v1 external-validation report also uses:

- Statlog German Credit, UCI 144, DOI `10.24432/C5NC77`, CC BY 4.0.
- Statlog Australian Credit Approval, UCI 143,
  DOI `10.24432/C59012`, CC BY 4.0.

Australian Credit Approval is an approval-class benchmark, not a documented
default target. It is not part of the v2 training union.

## Derived-artifact boundary

V2 versioned JSON/HTML evidence records source and model checksums, source and
harmonized row counts, target definitions, risk rates and missingness. The
1,200-profile decision demo is deterministic and synthetic. Publication now
proceeds under the repository owner's 14 August 2026 resolution attestation.
No source row, identifier or claimed production customer is intentionally
redistributed.
