# Synthetic incident report: proxy returns HTTP 502

**ID:** LAB-INC-001
**Environment:** Local Linux, Nginx reverse proxy, Python HTTP fixture, loopback only
**Severity:** Major within this exercise: the client cannot reach the application through its public-facing route
**Status:** Resolved in the controlled scenario; no real user or customer affected

## Symptom and reproduction

1. Start the healthy scenario. `GET /` through Nginx returns HTTP 200 with `incident-lab-ok`.
2. Change only `proxy_pass` to an unused loopback port. The same request returns HTTP 502.
3. Query the application directly at `/health`: it still returns HTTP 200.

Observed during both a scripted run and direct `curl` checks in paused manual mode: proxy status `200 → 502 → 200`; application health stayed `200 → 200 → 200`. In the incident state, the Nginx error log contained `connect() failed (111: Connection refused) ... while connecting to upstream`. The runner checks that failure class before declaring the scenario successful. Temporary logs are deleted after the run; the excerpt here omits runtime paths, ports and timestamps.

## Diagnosis and fix

The direct application health response ruled out an application outage. The Nginx error log showed an unsuccessful TCP connection to its configured upstream. Comparing `proxy_pass` with the application's listening port identified the mismatch. Restoring the correct upstream port and restarting only the local proxy restored HTTP 200 through the proxy.

## Verification and prevention

The local integration test checks the healthy response, the 502 incident, the refusal in the proxy log, continued application health, and the recovered response. A deployment check should validate the proxy configuration (`nginx -t`), verify the configured upstream port against the service listener, and run an end-to-end request through the proxy after a change. This exercise does not establish operational readiness outside the synthetic lab.
