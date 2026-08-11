# Configuration

[← Documentation hub](README.md)

Settings load in this order (later sources override earlier ones):

1. CLI flags
2. Environment variables
3. YAML config file
4. `.env` in the current working directory

## Product scoping

Each Cisco product reads only its own settings. In YAML, nest Nexus Dashboard keys under `nexus_dashboard:`; environment variables use the `ND_` prefix. Additional products will follow the same pattern with their own section and prefix.

## Config file locations

Resolved in order until one file exists:

- `--config /path/to/file`
- `ND_CONFIG`
- `./nac-analytics.yaml`
- `~/.config/nac-analytics/config.yaml`

## Nexus Dashboard variables

The authoritative key list and inline comments live in [config.example.yaml](../config.example.yaml). Summary:

| YAML key (under `nexus_dashboard:`) | Environment variable | Notes |
| --- | --- | --- |
| `host` | `ND_HOST` | Hostname or IP |
| `username` / `user` | `ND_USER` | Secret — prefer `.env` |
| `password` | `ND_PASSWORD` | Secret — prefer `.env` |
| `domain` | `ND_DOMAIN` | Login domain (e.g. `DefaultAuth`) |
| `fabric` | `ND_FABRIC` | Default ACI fabric |
| `fabrics` | — | List for `compliance --all` |
| `verify_ssl` / `verify_tls` | `ND_VERIFY_SSL` | `ND_VERIFY_TLS` alias accepted |
| `ca_bundle` | `ND_CA_BUNDLE` | Path to CA bundle |
| `job_timeout_minutes` | `ND_JOB_TIMEOUT_MINUTES` | Analysis job timeout |
| `poll_interval` | `ND_POLL_INTERVAL` | Job poll interval (seconds) |
| `delta_detail` | `ND_DELTA_DETAIL` | Default `--detail` for prechange/delta |

Minimal example:

```yaml
nexus_dashboard:
  host: nd.example.com
  domain: DefaultAuth
  fabric: FABRIC-A
```

Keep credentials out of committed YAML — use `.env` or your CI secret store (see [.env.example](../.env.example)).
