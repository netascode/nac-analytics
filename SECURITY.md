# Security

## Supported versions

| Version | Supported |
| --- | --- |
| 0.2.x | Yes |
| 0.1.x | Best effort |

## Reporting a vulnerability

Report security issues via [GitHub Issues](https://github.com/netascode/nac-analytics/issues). If your organisation requires private disclosure, note that in the issue and maintainers will follow up.

## Scope

- **Credentials:** Keep `ND_PASSWORD` and other secrets in `.env` or your CI secret store, not in committed YAML.
- **TLS:** Use `ND_VERIFY_SSL=true` (default) in production; set `ND_CA_BUNDLE` for private CAs.
- **Local artefacts:** JUnit reports and Terraform plan JSON may contain fabric details — treat them like operational data.

This tool connects to Nexus Dashboard over HTTPS and does not store credentials beyond the process lifetime.
