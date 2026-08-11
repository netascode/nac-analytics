# Command reference

[← Documentation hub](../README.md)

The CLI exposes help at three levels. Run `--help` at each tier, or use the captured blocks below.

| Level | Invocation | Document |
| --- | --- | --- |
| 1 — Global | `nac-analytics --help` | This page |
| 2 — Product | `nac-analytics nexus-dashboard --help` | [README § Nexus Dashboard](../README.md#nexus-dashboard-commands) |
| 3 — Verb | `nac-analytics nexus-dashboard <verb> --help` | [Nexus Dashboard commands](nexus-dashboard/README.md) |

## Global help

Product groups and the global `version` command.

<!-- BEGIN: help:root -->

```ansi
[1m                                                                                                    [0m
[1m [0m[1;33mUsage: [0m[1mnac-analytics [OPTIONS] COMMAND [ARGS]...[0m[1m                                                  [0m[1m [0m
[1m                                                                                                    [0m
 Change analytics for Cisco products.                                                               
                                                                                                    
 [2mRun a product group followed by a command, for example:[0m                                            
                                                                                                    
 [2m  nac-analytics nexus-dashboard doctor      (alias: nd)[0m                                            
                                                                                                    
 [2mEach product carries its own commands and configuration; see[0m                                       
 [2m`nac-analytics [0m[1;2;33m<product>[0m[2m [0m[1;2;36m-[0m[1;2;36m-help[0m[2m`. Products available today are listed below;[0m                       
 [2mmore Cisco products are planned.[0m                                                                   
                                                                                                    
[2m╭─[0m[2m Options [0m[2m───────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m-[0m[1;36m-help[0m          Show this message and exit.                                                      [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
[2m╭─[0m[2m Commands [0m[2m──────────────────────────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36mversion        [0m[1;36m [0m Print the version and exit.                                                     [2m│[0m
[2m│[0m [1;36mnexus-dashboard[0m[1;36m [0m Change analysis for Cisco Nexus Dashboard 4.2.1+ (GA REST APIs, ACI).           [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────────────────────────╯[0m
```

<!-- END: help:root -->

## Nexus Dashboard verbs

| Verb | Purpose |
| --- | --- |
| [prechange](nexus-dashboard/prechange.md) | Analyse a candidate config against current fabric state |
| [delta](nexus-dashboard/delta.md) | Compare two snapshots and report changes |
| [snapshots](nexus-dashboard/snapshots.md) | Resolve a snapshot ID (CI baseline pinning) |
| [compliance](nexus-dashboard/compliance.md) | Report compliance rule status |
| [doctor](nexus-dashboard/doctor.md) | Check connectivity, credentials, fabric visibility |
