# nac-analytics

> **In development** — install from source today; PyPI release planned.
> Formerly **nac-nd**. Today it covers Cisco ACI via Nexus Dashboard 4.2.1+; the intent is to grow beyond Nexus Dashboard and add support for additional Cisco products, so one tool can drive change analytics across platforms.

CLI for change analysis on Cisco ACI fabrics via Nexus Dashboard 4.2.1+.

Commands are grouped per Cisco product: `nac-analytics <product> <command>`.
Today the product is `nexus-dashboard` (alias `nd`); more products are planned.

## Installation

**Requirements:** Nexus Dashboard 4.2.1+, Python 3.10+, an ACI fabric registered in Nexus Dashboard.

```bash
git clone https://github.com/netascode/nac-analytics.git
cd nac-analytics
uv sync --group dev
uv run nac-analytics --help
```

## Quick start

```bash
cp config.example.yaml nac-analytics.yaml   # edit host, fabric, domain
cp .env.example .env                 # set ND_USER and ND_PASSWORD
uv run nac-analytics nd doctor
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success; threshold not breached |
| 1 | Unexpected error |
| 2 | Analysis job failed, stopped, vanished, or timed out |
| 3 | New anomalies at `--fail-on` (or compliance violations with `--fail-on-violations`) |
| 4 | Bad input, config, or configuration rejected by Nexus Dashboard |
| 5 | Authentication or authorisation failure |

## Nexus Dashboard commands

Product-level help (`nac-analytics nexus-dashboard --help`, alias `nd`). Verb-level flags and examples live in the [command reference](docs/commands/README.md).

<!-- If GitHub renders this block poorly, replace with docs/nexus-dashboard-help.png -->

<!-- BEGIN: help:nexus-dashboard -->

```ansi
[1m                                                                                                    [0m
[1m [0m[1;33mUsage: [0m[1mnac-analytics nexus-dashboard [OPTIONS] COMMAND [ARGS]...[0m[1m                                  [0m[1m [0m
[1m                                                                                                    [0m
 Change analysis for Cisco Nexus Dashboard 4.2.1+ (GA REST APIs, ACI).                              
                                                                                                    
 [2mConfiguration:[0m                                                                                     
 [2mND_HOST                 Nexus Dashboard hostname or IP[0m                                             
 [2mND_USER                 Login username[0m                                                             
 [2mND_PASSWORD             Login password[0m                                                             
 [2mND_DOMAIN               Login domain[0m                                                               
 [2mND_FABRIC               Default ACI fabric name[0m                                                    
 [2mND_VERIFY_SSL           Verify TLS certificate (ND_VERIFY_TLS accepted)[0m                            
 [2mND_CA_BUNDLE            Path to CA bundle[0m                                                          
 [2mND_JOB_TIMEOUT_MINUTES  Minutes to wait for analysis jobs[0m                                          
 [2mND_POLL_INTERVAL        Seconds between job status polls[0m                                           
 [2mND_DELTA_DETAIL         Default [0m[1;2;36m-[0m[1;2;36m-detail[0m[2m for prechange and delta[0m                                   
 [2mND_CONFIG               Path to YAML config file[0m                                                   
                                                                                                    
 [2mIn YAML, nest these under a `nexus_dashboard:` section. Settings load from[0m                         
 [2mCLI flags, then environment variables, nac-analytics.yaml, or .env.[0m                                
                                                                                                    
[2m╭─[0m[2m Options [0m[2m───────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m-[0m[1;36m-help[0m          Show this message and exit.                                                      [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
[2m╭─[0m[2m Commands [0m[2m──────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36mprechange [0m[1;36m [0m Analyse a candidate configuration against a fabric's current state.                  [2m│[0m
[2m│[0m [1;36mdelta     [0m[1;36m [0m Compare two snapshots of a fabric and report what changed.                           [2m│[0m
[2m│[0m [1;36msnapshots [0m[1;36m [0m Resolve a fabric snapshot and print its ID (for CI baseline pinning).                [2m│[0m
[2m│[0m [1;36mcompliance[0m[1;36m [0m Report compliance rule status for a fabric (or every fabric with [1;36m-[0m[1;36m-all[0m).             [2m│[0m
[2m│[0m [1;36mdoctor    [0m[1;36m [0m Check connectivity, credentials, and fabric visibility.                              [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
```

<!-- END: help:nexus-dashboard -->

## Configuration

Precedence: CLI flags → environment variables → YAML → `.env` in cwd.

Settings are scoped per product. See [config.example.yaml](config.example.yaml) and [Configuration](docs/configuration.md) for the full variable list and YAML layout.

## Documentation

| Topic | Link |
| --- | --- |
| Documentation hub | [docs/README.md](docs/README.md) |
| Command reference (global + verbs) | [docs/commands/README.md](docs/commands/README.md) |
| Configuration | [docs/configuration.md](docs/configuration.md) |
| Development | [docs/development.md](docs/development.md) |
| Examples & CI pipeline | [examples/README.md](examples/README.md) |

## Development

Contributors: see [Development](docs/development.md). After changing CLI help text, run `uv run python scripts/capture-help.py`.
