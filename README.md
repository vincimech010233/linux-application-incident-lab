# Linux Application Incident Lab

Synthetic, local exercise in application support and Linux service recovery. A client requests an Nginx reverse proxy, which forwards to a small Python HTTP service. The incident changes only Nginx's upstream port; it leaves the application healthy.

## Reproduce

Requirements: Linux, Python 3.10+, and an installed Nginx binary. No Python packages, root privileges, Docker, external services, or credentials are required.

```bash
python3 run_scenario.py --nginx /path/to/nginx
NGINX_BIN=/path/to/nginx python3 -m unittest discover -s tests -v
python3 run_scenario.py --manual --nginx /path/to/nginx
```

If `nginx` is on `PATH`, the `--nginx` option is optional. The scenario picks unprivileged ephemeral ports, binds both services to `127.0.0.1`, validates each Nginx configuration with `nginx -t`, and runs the three states in order. Temporary configurations and logs stay under `.runtime/` and are removed; each service process is stopped in a `finally` block. A concurrent process can claim an ephemeral port between selection and binding; a failed run should be retried rather than treated as incident evidence.

`--manual` pauses at each state and prints the current proxy and upstream URLs. While paused, request both URLs with `curl --noproxy '*' -i URL`, record the status/body, and press Enter to advance. The ports change between runs; do not copy them into published evidence.

| State | Application `/health` | Proxy `/` | Interpretation |
| --- | ---: | ---: | --- |
| Healthy | 200 | 200 | Proxy reaches the application |
| Incident | 200 | 502 | Proxy targets an unused port |
| Recovered | 200 | 200 | Upstream port corrected |

The proxy error log must contain `connect() failed (111: Connection refused)` in the incident state. The runner prints only status codes, a fixed response marker, and whether this log signature was seen. It does not export host logs, addresses, timestamps, or absolute paths.

## Evidence and QA

- [Incident report](docs/incident-report.md): symptom, reproduction, impact and resolution.
- [Manual test case](docs/manual-test-case.md): before/after QA check with observed results.
- [Root cause analysis](docs/root-cause-analysis.md): hypothesis checks, cause and prevention.
- `tests/test_scenario.py`: live local integration test of 200 → 502 → 200 and upstream health throughout.

The exercise uses one Nginx worker and one single-threaded Python HTTP service. It demonstrates a synthetic support workflow, not a real customer incident or a production deployment. It does not demonstrate Docker operation; Nginx was used directly because Docker was unavailable in the execution environment.
