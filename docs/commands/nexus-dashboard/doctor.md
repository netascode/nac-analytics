# doctor

[← Nexus Dashboard commands](README.md) · [Command reference](../README.md)

Read-only check of connectivity, credentials, and fabric visibility. Creates no analysis jobs — use this first after configuring `nac-analytics.yaml` and `.env`.

## Examples

```bash
nac-analytics nd doctor
nac-analytics nd doctor -output json
```

## Help

<!-- BEGIN: help:doctor -->

```ansi
[1m                                                                                                    [0m
[1m [0m[1;33mUsage: [0m[1mnac-analytics nexus-dashboard doctor [OPTIONS][0m[1m                                             [0m[1m [0m
[1m                                                                                                    [0m
 Check connectivity, credentials, and fabric visibility.                                            
                                                                                                    
 [2mRead-only; creates no jobs. Requires the same connection settings as other[0m                         
 [2mcommands ([0m[1;2;36m-[0m[1;2;36m-host[0m[2m, credentials, [0m[1;2;36m-[0m[1;2;36m-fabric[0m[2m or ND_FABRIC).[0m                                             
                                                                                                    
[2m╭─[0m[2m Options [0m[2m───────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m-[0m[1;36m-host[0m                               [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Nexus Dashboard hostname or IP. [2;33m[env var: ND_HOST][0m   [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-username[0m    [1;32m-u[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login username. [2;33m[env var: ND_USER][0m                   [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-password[0m                           [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login password. [2;33m[env var: ND_PASSWORD][0m               [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-domain[0m                             [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Login domain; ND requires one. [2;33m[env var: ND_DOMAIN][0m  [2m│[0m
[2m│[0m                                             [2m[default: DefaultAuth]        [0m                       [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-fabric[0m      [1;32m-f[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  ACI fabric name (or set via YAML `fabric` /          [2m│[0m
[2m│[0m                                             ND_FABRIC).                                          [2m│[0m
[2m│[0m                                             [2;33m[env var: ND_FABRIC]                                [0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-output[0m      [1;32m-o[0m                     [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Output format: text, json, yaml, markdown, junit.    [2m│[0m
[2m│[0m                                             junit writes one test case per [1;36m-[0m[1;36m-fail[0m[1;36m-on[0m severity    [2m│[0m
[2m│[0m                                             (prechange/delta).                                   [2m│[0m
[2m│[0m                                             [2m[default: text]                                     [0m [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-verify[0m[1;36m-ssl[0m      [1;35m-[0m[1;35m-no[0m[1;35m-verify-ssl[0m    [1;33m     [0m  Verify the cluster's TLS certificate.                [2m│[0m
[2m│[0m                                             [2;33m[env var: ND_VERIFY_SSL]             [0m                [2m│[0m
[2m│[0m                                             [2m[default: verify-ssl]                [0m                [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-ca[0m[1;36m-bundle[0m                          [1;2;33m<[0m[1;33mstr[0m[1;2;33m>[0m  Path to a CA bundle. [2;33m[env var: ND_CA_BUNDLE][0m         [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-verbose[0m     [1;32m-v[0m                     [1;33m     [0m  Log each HTTP request and API call.                  [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-help[0m                               [1;33m     [0m  Show this message and exit.                          [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
```

<!-- END: help:doctor -->
