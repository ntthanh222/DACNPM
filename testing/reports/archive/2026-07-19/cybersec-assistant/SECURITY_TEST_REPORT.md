# Security test report

Read-only local checks performed 2026-07-16:

| Area | Result |
|---|---|
| Anonymous admin authorization boundary | 31/31 PASS (401/403) |
| Private key / dangerous-call source scan | No matches in scoped source |
| Plaintext QA password literal scan | PASS after removing capture-script fallbacks |
| Container privilege inspection | backend/crawler/actions non-root, not privileged, no added caps |
| Authenticated IDOR/BOLA and privilege matrix | NOT VERIFIED; QA fixture blocked |
| SSRF full matrix | NOT VERIFIED in this run |
| Dependency CVE scan | NOT RUN; scanners unavailable |
| Docker image CVE scan | NOT RUN; scanner unavailable |

No destructive exploitation or external target probing was performed.
