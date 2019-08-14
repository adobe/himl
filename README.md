# hierarchical-yaml
A hierarchical config using yaml in Python

Latest version is: 0.1.3


## Installation

### Using `pip`

```sh
pip install hierarchical-yaml
```

### From Source

```
git clone https://github.com/adobe/hierarchical-yaml
cd hierarchical-yaml
sudo python setup.py install
```

## Example

### Using the cli

```sh
usage: hyaml [-h] [--output-file OUTPUT_FILE] [--format OUTPUT_FORMAT]
             [--filter FILTER] [--exclude EXCLUDE]
             [--skip-interpolation-validation]
             [--skip-interpolation-resolving] [--enclosing-key ENCLOSING_KEY]
             [--cwd CWD]
             path
```

```sh
hyaml examples/config_example/env=dev/region=us-east-1/cluster=cluster2
```

The configuration output will be something like this:
```
cluster:
  description: 'This is cluster: cluster2. It is using c3.2xlarge instance type.'
  name: cluster2
  node_type: c3.2xlarge
region:
  location: us-east-1
env: dev
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
