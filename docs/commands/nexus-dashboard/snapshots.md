# snapshots

[← Nexus Dashboard commands](README.md) · [Command reference](../README.md)

Resolve a fabric snapshot selector and print its ID. Use in CI to pin baselines before and after a change.

Selectors: `latest`, `latest-N`, or a concrete `snapshotId`. Combine with `-since` / `-until` when the API's 50-record listing cap requires narrowing the window.

## Examples

```bash
nac-analytics nd snapshots latest
SNAP=$(nac-analytics nd snapshots latest)
nac-analytics nd snapshots -output json latest-1
```

## Help

<!-- BEGIN: help:snapshots -->

```ansi
[1m                                                                                                    [0m
[1m [0m[1;33mUsage: [0m[1mnac-analytics nexus-dashboard snapshots [OPTIONS] {selector}[0m[1m                               [0m[1m [0m
[1m                                                                                                    [0m
 Resolve a fabric snapshot and print its ID (for CI baseline pinning).                              
                                                                                                    
[2m╭─[0m[2m Arguments [0m[2m─────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [31m*[0m    selector      [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Snapshot to resolve: 'latest', 'latest-N', or a snapshotId. [2;31m[required][0m [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
[2m╭─[0m[2m Options [0m[2m───────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m-[0m[1;36m-host[0m                               [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Nexus Dashboard hostname or IP. [2;33m[env var: ND_HOST][0m   [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-username[0m    [1;32m-u[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login username. [2;33m[env var: ND_USER][0m                   [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-password[0m                           [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login password. [2;33m[env var: ND_PASSWORD][0m               [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-domain[0m                             [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login domain; ND requires one. [2;33m[env var: ND_DOMAIN][0m  [2m│[0m
[2m│[0m                                             [2m[default: DefaultAuth]        [0m                       [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-fabric[0m      [1;32m-f[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  ACI fabric name (or set via YAML `fabric` /          [2m│[0m
[2m│[0m                                             ND_FABRIC).                                          [2m│[0m
[2m│[0m                                             [2;33m[env var: ND_FABRIC]                                [0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-since[0m                              [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  When resolving snapshots, only consider those        [2m│[0m
[2m│[0m                                             collected on or after this ISO-8601 timestamp (works [2m│[0m
[2m│[0m                                             around the API's 50-record listing cap).             [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-until[0m                              [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  When resolving snapshots, only consider those        [2m│[0m
[2m│[0m                                             collected on or before this ISO-8601 timestamp.      [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-output[0m      [1;32m-o[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Output format: text (snapshot ID only), json, or     [2m│[0m
[2m│[0m                                             yaml.                                                [2m│[0m
[2m│[0m                                             [2m[default: text]                                     [0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-verify[0m[1;36m-ssl[0m      [1;35m-[0m[1;35m-no[0m[1;35m-verify-ssl[0m    [1;33m     [0m  Verify the cluster's TLS certificate.                [2m│[0m
[2m│[0m                                             [2;33m[env var: ND_VERIFY_SSL]             [0m                [2m│[0m
[2m│[0m                                             [2m[default: verify-ssl]                [0m                [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-ca[0m[1;36m-bundle[0m                          [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Path to a CA bundle. [2;33m[env var: ND_CA_BUNDLE][0m         [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-verbose[0m     [1;32m-v[0m                     [1;33m     [0m  Log each HTTP request and API call.                  [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-help[0m                               [1;33m     [0m  Show this message and exit.                          [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
```

<!-- END: help:snapshots -->
