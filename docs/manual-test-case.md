# Manual QA case: proxy upstream mismatch

**Test ID:** LAB-QA-001
**Type:** Functional regression / service recovery
**Environment:** Synthetic local Nginx and Python fixture on loopback
**Severity if observed in a deployed application:** Major, because the client route is unavailable
**Execution status:** Executed locally with direct `curl` requests during each paused state; no real product or customer was tested

## Preconditions

- Linux, Python 3.10+, and an Nginx executable are available.
- Ports chosen by the runner are free and the operator is unprivileged.
- The repository contains no real user data or credentials.

## Steps and results

Run `python3 run_scenario.py --manual --nginx /path/to/nginx`. At each pause, use the two loopback URLs printed by the runner, then press Enter. The table records a local execution; ephemeral port numbers and HTTP date headers were intentionally omitted.

| Step | Manual action | Expected | Observed locally |
| --- | --- | --- | --- |
| 1 | In `healthy`, `curl --noproxy '*' -i` the proxy `/` and direct upstream `/health` | Proxy `200` with `incident-lab-ok`; upstream `200` | Both `200`; expected bodies present |
| 2 | In `incident`, request the same two routes | Proxy `502`; upstream still `200` | Proxy `502 Bad Gateway`; upstream `200` with the expected health JSON |
| 3 | Inspect the temporary Nginx error log for the refused upstream connection | `connect() failed (111: Connection refused)` | Signature present |
| 4 | In `recovered`, repeat both requests | Proxy and upstream `200`; proxy body restored | Both `200`; `incident-lab-ok` restored |
| 5 | Press Enter to finish and check the runner's exit status | Exit 0; own processes and temporary logs removed | Exit 0; no scenario files retained |

**Defect state before correction:** Reproduced in the controlled misroute.
**Defect state after correction:** No longer reproduced; recovery check passed.
**Evidence:** Direct HTTP status/body checks, the refusal signature observed in Nginx's temporary error log, the runner summary, and the independent integration test. The raw log is not retained in the repository.

This is a manual HTTP check in a locally orchestrated scenario. It does not claim an end-user UI test or external defect report.
