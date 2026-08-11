# delta

[← Nexus Dashboard commands](README.md) · [Command reference](../README.md)

Compare two snapshots of a fabric and report what changed. With no arguments, defaults to **latest-1** vs **latest**. Writes JUnit to `delta-report.xml` by default and exits **3** on new critical/major anomalies.

Pin snapshots in CI: capture IDs with [snapshots](snapshots.md), apply your change, then pass both IDs to delta.

## Examples

```bash
nac-analytics nd delta                         # latest-1 vs latest
nac-analytics nd delta abc-123                 # pinned pre, post = latest
nac-analytics nd delta abc-123 def-456         # both pinned
nac-analytics nd delta -output text abc def
```

## Help

<!-- BEGIN: help:delta -->

```ansi
[1m                                                                                                    [0m
[1m [0m[1;33mUsage: [0m[1mnac-analytics nexus-dashboard delta [OPTIONS] [pre] [post][0m[1m                                 [0m[1m [0m
[1m                                                                                                    [0m
 Compare two snapshots of a fabric and report what changed.                                         
                                                                                                    
 [2;33mUsage: [0m[2mnac-analytics delta [0m[2m [0m[2m — defaults to latest-1 vs latest.[0m                                     
 [2mBy default writes JUnit to delta-report.xml and exits 3 on critical/major.[0m                         
                                                                                                    
[2m╭─[0m[2m Arguments [0m[2m─────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m   pre       [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Pre-change snapshot: 'latest', 'latest-N', or a snapshotId.                   [2m│[0m
[2m│[0m   post      [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Post-change snapshot: 'latest', 'latest-N', or a snapshotId.                  [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
[2m╭─[0m[2m Options [0m[2m───────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m-[0m[1;36m-host[0m                                         [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Nexus Dashboard hostname or IP.            [2m│[0m
[2m│[0m                                                       [2;33m[env var: ND_HOST]             [0m            [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-username[0m              [1;32m-u[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login username. [2;33m[env var: ND_USER][0m         [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-password[0m                                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login password. [2;33m[env var: ND_PASSWORD][0m     [2m│[0m

[2m│[0m [1;36m-[0m[1;36m-domain[0m                                       [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login domain; ND requires one.             [2m│[0m
[2m│[0m                                                       [2;33m[env var: ND_DOMAIN]          [0m             [2m│[0m
[2m│[0m                                                       [2m[default: DefaultAuth]        [0m             [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-fabric[0m                [1;32m-f[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  ACI fabric name (or set via YAML `fabric`  [2m│[0m
[2m│[0m                                                       / ND_FABRIC).                              [2m│[0m
[2m│[0m                                                       [2;33m[env var: ND_FABRIC]                      [0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-name[0m                                         [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Job name; generated when omitted.          [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-fail[0m[1;36m-on[0m                                      [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Comma-separated severities whose new       [2m│[0m
[2m│[0m                                                       anomalies fail the run (exit 3); default   [2m│[0m
[2m│[0m                                                       critical,major. Use 'none' to report only. [2m│[0m
[2m│[0m                                                       [2m[default: critical,major]                 [0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-include[0m[1;36m-acknowledged[0m                         [1;33m     [0m  Count anomalies that have been             [2m│[0m
[2m│[0m                                                       acknowledged in Nexus Dashboard.           [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-since[0m                                        [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  When resolving snapshots, only consider    [2m│[0m
[2m│[0m                                                       those collected on or after this ISO-8601  [2m│[0m
[2m│[0m                                                       timestamp (works around the API's          [2m│[0m
[2m│[0m                                                       50-record listing cap).                    [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-until[0m                                        [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  When resolving snapshots, only consider    [2m│[0m
[2m│[0m                                                       those collected on or before this ISO-8601 [2m│[0m
[2m│[0m                                                       timestamp.                                 [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-cleanup[0m                   [1;35m-[0m[1;35m-keep[0m             [1;33m     [0m  Delete analysis job(s) created by this run [2m│[0m
[2m│[0m                                                       when finished. prechange also leaves its   [2m│[0m
[2m│[0m                                                       snapshot on the fabric.                    [2m│[0m
[2m│[0m                                                       [2m[default: keep]                           [0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-detail[0m                                       [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Extra delta detail on prechange and delta  [2m│[0m
[2m│[0m                                                       beyond severity counts: none, resources,   [2m│[0m
[2m│[0m                                                       anomalies, policy-diff, full. Default full [2m│[0m
[2m│[0m                                                       on prechange (resources on delta). Legacy  [2m│[0m
[2m│[0m                                                       values 'all' and 'summary' map to full and [2m│[0m
[2m│[0m                                                       none.                                      [2m│[0m
[2m│[0m                                                       [2;33m[env var: ND_DELTA_DETAIL]                [0m [2m│[0m
[2m│[0m                                                       [2m[default: resources]                      [0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-output[0m                [1;32m-o[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Output format: text, json, yaml, markdown, [2m│[0m
[2m│[0m                                                       junit. Gate commands default to junit      [2m│[0m
[2m│[0m                                                       (written to [1;36m-[0m[1;36m-report[0m[1;36m-file[0m).                [2m│[0m
[2m│[0m                                                       [2m[default: junit]                          [0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-report[0m[1;36m-file[0m                                  [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  JUnit report path for prechange/delta      [2m│[0m
[2m│[0m                                                       (default: prechange-report.xml or          [2m│[0m
[2m│[0m                                                       delta-report.xml). Use '-' for stdout.     [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-verify[0m[1;36m-ssl[0m                [1;35m-[0m[1;35m-no[0m[1;35m-verify-ssl[0m    [1;33m     [0m  Verify the cluster's TLS certificate.      [2m│[0m
[2m│[0m                                                       [2;33m[env var: ND_VERIFY_SSL]             [0m      [2m│[0m
[2m│[0m                                                       [2m[default: verify-ssl]                [0m      [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-ca[0m[1;36m-bundle[0m                                    [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Path to a CA bundle.                       [2m│[0m
[2m│[0m                                                       [2;33m[env var: ND_CA_BUNDLE][0m                    [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-timeout[0m                                      [1;2;33m<[0m[1;33mint[0m[1;2;33m>[0m  Minutes to wait for an analysis job.       [2m│[0m
[2m│[0m                                                       [2;33m[env var: ND_JOB_TIMEOUT_MINUTES]   [0m       [2m│[0m
[2m│[0m                                                       [2m[default: 30]                       [0m       [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-poll[0m[1;36m-interval[0m                                [1;2;33m<[0m[1;33mint[0m[1;2;33m>[0m  Seconds between job status polls.          [2m│[0m
[2m│[0m                                                       [2;33m[env var: ND_POLL_INTERVAL]      [0m          [2m│[0m
[2m│[0m                                                       [2m[default: 15]                    [0m          [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-verbose[0m               [1;32m-v[0m                     [1;33m     [0m  Log each HTTP request and API call.        [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-help[0m                                         [1;33m     [0m  Show this message and exit.                [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
```

<!-- END: help:delta -->
