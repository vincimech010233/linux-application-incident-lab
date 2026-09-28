# Root cause analysis: wrong reverse-proxy upstream port

## Evidence chain

1. **Symptom:** A client request through the proxy changed from HTTP 200 to HTTP 502.
2. **Application check:** A direct `GET /health` still returned HTTP 200. The application process was reachable on its configured loopback port.
3. **Proxy check:** Nginx reported `connect() failed (111: Connection refused)` when connecting to its upstream.
4. **Configuration comparison:** The incident `proxy_pass` port differed from the application listener. No application code or response was changed.
5. **Correction:** The proxy's upstream port was set back to the application port. The client request returned HTTP 200 again.

## Conclusion and scope

The controlled root cause is a proxy/backend port mismatch. The direct health check and refusal log distinguish it from an application process failure in this run. Other causes of HTTP 502 are possible in real deployments and would require their own evidence.

## Preventive controls

- Keep the backend endpoint in one reviewed configuration value rather than copying ports by hand.
- Run `nginx -t` before activation.
- Check both direct backend health and a client request through the proxy after configuration changes.
- Preserve proxy error logs during real incidents under the organization's retention and privacy rules.
