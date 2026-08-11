# compliance

[← Nexus Dashboard commands](README.md) · [Command reference](../README.md)

Report compliance rule status for a fabric. Use `--all` to check every fabric listed in YAML `fabrics` (or the single default fabric). Exits **3** with `--fail-on-violations` when any rule is violated.

## Examples

```bash
nac-analytics nd compliance
nac-analytics nd compliance --all --fail-on-violations
nac-analytics nd compliance -snapshot latest-1 -output junit
```

## Help

<!-- BEGIN: help:compliance -->

```ansi
[1m                                                                                                    [0m
[1m [0m[1;33mUsage: [0m[1mnac-analytics nexus-dashboard compliance [OPTIONS][0m[1m                                         [0m[1m [0m
[1m                                                                                                    [0m
 Report compliance rule status for a fabric (or every fabric with [1;36m-[0m[1;36m-all[0m).                           
                                                                                                    
 [2mExits 3 with [0m[1;2;36m-[0m[1;2;36m-fail[0m[1;2;36m-on-violations[0m[2m when any rule is violated.[0m                                       
                                                                                                    
[2m╭─[0m[2m Options [0m[2m───────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m-[0m[1;36m-host[0m                                       [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Nexus Dashboard hostname or IP.              [2m│[0m
[2m│[0m                                                     [2;33m[env var: ND_HOST]             [0m              [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-username[0m            [1;32m-u[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login username. [2;33m[env var: ND_USER][0m           [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-password[0m                                   [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login password. [2;33m[env var: ND_PASSWORD][0m       [2m│[0m

[2m│[0m [1;36m-[0m[1;36m-domain[0m                                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login domain; ND requires one.               [2m│[0m
[2m│[0m                                                     [2;33m[env var: ND_DOMAIN]          [0m               [2m│[0m
[2m│[0m                                                     [2m[default: DefaultAuth]        [0m               [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-fabric[0m              [1;32m-f[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  ACI fabric name (or set via YAML `fabric` /  [2m│[0m
[2m│[0m                                                     ND_FABRIC).                                  [2m│[0m
[2m│[0m                                                     [2;33m[env var: ND_FABRIC]                        [0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-snapshot[0m                                   [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Resolve this snapshot ('latest', 'latest-N', [2m│[0m
[2m│[0m                                                     or an ID) and report compliance for its      [2m│[0m
[2m│[0m                                                     collection time instead of the newest run.   [2m│[0m
[2m│[0m                                                     Combine with [1;36m-[0m[1;36m-since[0m/[1;36m-[0m[1;36m-until[0m when needed.    [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-fail[0m[1;36m-on-violations[0m                         [1;33m     [0m  Exit 3 when any compliance rule is violated. [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-all[0m                                        [1;33m     [0m  Report compliance for every fabric in YAML   [2m│[0m
[2m│[0m                                                     `fabrics`, or the single YAML `fabric` /     [2m│[0m
[2m│[0m                                                     ND_FABRIC when no list is set.               [2m│[0m

[2m│[0m [1;36m-[0m[1;36m-since[0m                                      [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  When resolving snapshots, only consider      [2m│[0m
[2m│[0m                                                     those collected on or after this ISO-8601    [2m│[0m
[2m│[0m                                                     timestamp (works around the API's 50-record  [2m│[0m
[2m│[0m                                                     listing cap).                                [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-until[0m                                      [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  When resolving snapshots, only consider      [2m│[0m
[2m│[0m                                                     those collected on or before this ISO-8601   [2m│[0m
[2m│[0m                                                     timestamp.                                   [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-output[0m              [1;32m-o[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Output format: text, json, yaml, markdown,   [2m│[0m
[2m│[0m                                                     junit. junit writes one test case per        [2m│[0m
[2m│[0m                                                     [1;36m-[0m[1;36m-fail[0m[1;36m-on[0m severity (prechange/delta).        [2m│[0m
[2m│[0m                                                     [2m[default: text]                             [0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-verify[0m[1;36m-ssl[0m              [1;35m-[0m[1;35m-no[0m[1;35m-verify-ssl[0m    [1;33m     [0m  Verify the cluster's TLS certificate.        [2m│[0m
[2m│[0m                                                     [2;33m[env var: ND_VERIFY_SSL]             [0m        [2m│[0m
[2m│[0m                                                     [2m[default: verify-ssl]                [0m        [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-ca[0m[1;36m-bundle[0m                                  [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Path to a CA bundle. [2;33m[env var: ND_CA_BUNDLE][0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-timeout[0m                                    [1;2;33m<[0m[1;33mint[0m[1;2;33m>[0m  Minutes to wait for an analysis job.         [2m│[0m
[2m│[0m                                                     [2;33m[env var: ND_JOB_TIMEOUT_MINUTES]   [0m         [2m│[0m
[2m│[0m                                                     [2m[default: 30]                       [0m         [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-poll[0m[1;36m-interval[0m                              [1;2;33m<[0m[1;33mint[0m[1;2;33m>[0m  Seconds between job status polls.            [2m│[0m
[2m│[0m                                                     [2;33m[env var: ND_POLL_INTERVAL]      [0m            [2m│[0m
[2m│[0m                                                     [2m[default: 15]                    [0m            [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-verbose[0m             [1;32m-v[0m                     [1;33m     [0m  Log each HTTP request and API call.          [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-help[0m                                       [1;33m     [0m  Show this message and exit.                  [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
```

<!-- END: help:compliance -->
