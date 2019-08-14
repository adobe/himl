# hierarchical-yaml
A hierarchical config using yaml in Python

Latest version is: 0.1.2


## Installation

## Example

### Using the cli
```sh
hyaml examples/config_example/env=dev/region=us-east-1/cluster=cluster2
```

Where the examples folder looks something like this:
```
$ tree examples/config_example
examples/config_example
├── default.yaml
├── env=dev
│   ├── env.yaml
│   ├── region=us-east-1
│   │   ├── cluster=cluster1
│   │   │   └── cluster.yaml
│   │   ├── cluster=cluster2
│   │   │   └── cluster.yaml
│   │   └── region.yaml
│   └── region=us-west-2
│       ├── cluster=cluster1
│       │   └── cluster.yaml
│       └── region.yaml
└── env=prod
    ├── env.yaml
    └── region=eu-west-2
        ├── cluster=ireland1
        │   └── cluster.yaml
        └── region.yaml
```
