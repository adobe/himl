# himl
A hierarchical config using yaml in Python.

Latest version is: 0.11.0

## Description

A python module which allows you to merge hierarchical config files using YAML syntax. It offers deep merge, variable interpolation and secrets retrieval from secrets managers.

It is ideal if you want to structure your hierarchy in such a way that you avoid duplication. You can define a structure for your configuration using a hierarchy such environment/project/cluster/app. It is up to you what layers you want to use in this hierarchy. The tool will read all yaml files starting from the root (where default values would be) all the way to the leaf (where most specific values would be, which will take precedence).

Idea came from puppet's hiera.

## Table of Contents

- [himl](#himl)
  - [Description](#description)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
    - [Using `pip`](#using-pip)
    - [Using `docker` image](#using-docker-image)
    - [From Source](#from-source)
  - [Examples](#examples)
    - [Using the python module](#using-the-python-module)
    - [Using the cli](#using-the-cli)
  - [Features](#features)
    - [Interpolation](#interpolation)
      - [Interpolating simple values](#interpolating-simple-values)
      - [Interpolating whole `dict`](#interpolating-whole-dict)
    - [Deep merge](#deep-merge)
    - [Secrets retrieval](#secrets-retrieval)
      - [AWS SSM](#aws-ssm)
      - [AWS S3](#aws-s3)
      - [Vault](#vault)
    - [Merge with Terraform remote state](#merge-with-terraform-remote-state)
    - [Merge with env variables](#merge-with-env-variables)
  - [himl config merger](#himl-config-merger)
    - [Extra merger features](#extra-merger-features)

## Installation

### Using `pip`

```sh
pip install himl
```

### Using `docker` image

```sh
docker run ghcr.io/adobe/himl:latest himl-config-merger --help
```
See all docker tags at: https://github.com/adobe/himl/pkgs/container/himl/versions

### From Source

```
git clone https://github.com/adobe/himl
cd himl
sudo python install -e .
```

## Examples

### Using the python module

This will merge simple/default.yaml with simple/production/env.yaml
```py
from himl import ConfigProcessor

config_processor = ConfigProcessor()
path = "examples/simple/production"
filters = () # can choose to output only specific keys
exclude_keys = () # can choose to remove specific keys
output_format = "yaml" # yaml/json


config_processor.process(path=path, filters=filters, exclude_keys=exclude_keys,
                         output_format=output_format, print_data=True)

```

The above example will merge `simple/default.yaml` with `simple/production/env.yaml`:
```
$ tree examples/simple
examples/simple
├── default.yaml
└── production
    └── env.yaml
```

The example also showcases deep merging of lists and maps.

`examples/simple/default.yaml`
```yaml
---
env: default
deep:
  key1: v1
  key2: v2
deep_list:
  - item1
  - item2
```

`examples/simple/production/env.yaml`
```yaml
---
env: prod
deep:
  key3: v3
deep_list:
  - item3
```

Result:
```yaml
env: prod
deep:
  key1: v1
  key2: v2
  key3: v3
deep_list:
- item1
- item2
- item3
```

### Using the cli

A cli tool called `himl` is automatically installed via `pip`. You can use it to parse a tree of yamls and it will either output the combined configuration at standard output or write it to a file.

```sh
usage: himl [-h] [--output-file OUTPUT_FILE] [--format OUTPUT_FORMAT]
             [--filter FILTER] [--exclude EXCLUDE]
             [--skip-interpolation-validation]
             [--skip-interpolation-resolving] [--enclosing-key ENCLOSING_KEY]
             [--cwd CWD]
             [--list-merge-strategy {append,override,prepend,append_unique}]
             path
```

```sh
himl examples/complex/env=dev/region=us-east-1/cluster=cluster2
```

Based on the configuration tree from the [examples/complex](examples/complex) folder, the output of the above command will be the following:
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
$ tree examples/complex
examples/complex
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

## Features

### Interpolation

In order to avoid repetition, we wanted to make it possible to define a value once and reuse it in other parts of the yaml config.
Unlike yaml anchors, these interpolations work across multiple files.

#### Interpolating simple values

`data/default.yaml`:
```yaml
allowed_roles:
  - "arn:aws:iam::{{account.id}}:role/myrole"
```

`data/dev/env.yaml`:
```
account:
  id: "123456"
```

#### Interpolating whole `dict`

```yaml
projects:
  webapp1:
    tagging:
      Owner: "Web Service Team"
      Environment: "dev"
      CostCenter: "123"
  data-store:
      Owner: "Backend Team"
      Environment: "dev"
      CostCenter: "455"

# this will copy the whole projects.webapp1.tagging dict to this key
tagging: "{{projects.webapp1.tagging}}"

# or even a double interpolation
tagging: "{{projects.{{project.name}}.tagging}}"
```

### Deep merge

It's possible to have the same key (eg. a dict/list) in multiple files and combine them using a deep merge.
See an example [here](https://github.com/adobe/himl#deep-merge-example).

### Secrets retrieval

#### [AWS SSM](https://docs.aws.amazon.com/systems-manager/latest/userguide/integration-ps-secretsmanager.html)

```yaml
passphrase: "{{ssm.path(/key/coming/from/aws/secrets/store/manager).aws_profile(myprofile)}}"
```

#### [AWS S3](https://aws.amazon.com/s3/)

```yaml
my_value: "{{s3.bucket(my-bucket).path(path/to/file.txt).base64encode(true).aws_profile(myprofile)}}"
```

#### [Vault](https://www.vaultproject.io/)

Use vault cli to authenticate, fallback method via LDAP.

Retrieve only one key value from a secret, the path tail is used as key:
```yaml
my_value: "{{vault.key(/path/from/vault/key)}}"
```

Retrieve all key/value pairs from a vault path:
```yaml
my_dict: "{{vault.path(/path/from/vault)}}"
```

Generate a token for a policy:
```yaml
my_token: "{{vault.token_policy(my_vault_policy)}}"
```

### Merge with [Terraform remote state](https://www.terraform.io/docs/state/remote.html)

```yaml
### Terraform remote states ###
remote_states:
  - name: cluster_composition
    type: terraform
    aws_profile: "my_aws_profile"
    s3_bucket: "my_terraform_bucket"
    s3_key: "mycluster.tfstate"


endpoint: "{{outputs.cluster_composition.output.value.redis_endpoint}}"
```

### Merge with env variables
```yaml
kubeconfig_location: {{env(KUBECONFIG)}}
```


## himl config merger

The `himl-config-merger` script, contains logic of merging a hierarchical config directory and creating the end result YAML files.

```sh
himl-config-merger examples/complex --output-dir merged_output --levels env region cluster --leaf-directories cluster
```

```
INFO:__main__:Found input config directory: examples/complex/env=prod/region=eu-west-2/cluster=ireland1
INFO:__main__:Storing generated config to: merged_output/prod/eu-west-2/ireland1.yaml
INFO:__main__:Found input config directory: examples/complex/env=dev/region=us-west-2/cluster=cluster1
INFO:__main__:Storing generated config to: merged_output/dev/us-west-2/cluster1.yaml
INFO:__main__:Found input config directory: examples/complex/env=dev/region=us-east-1/cluster=cluster1
INFO:__main__:Storing generated config to: merged_output/dev/us-east-1/cluster1.yaml
INFO:__main__:Found input config directory: examples/complex/env=dev/region=us-east-1/cluster=cluster2
INFO:__main__:Storing generated config to: merged_output/dev/us-east-1/cluster2.yaml
```

Input example:
```
> tree examples/complex
examples/complex
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

Output:
```
merged_output
├── dev
│   ├── us-east-1
│   │   ├── cluster1.yaml
│   │   └── cluster2.yaml
│   └── us-west-2
│       └── cluster1.yaml
└── prod
    └── eu-west-2
        └── ireland1.yaml
```

Leveraging HIML, the config-merger script loads the configs tree structure and deep-merges all keys from all YAML files found from a root path to an edge. For each leaf directory, a file will be created under `--output-dir`.

Under each level, there is a mandatory "level key" that is used by config-merger for computing the end result. This key should be present in one of the files under each level. (eg. env.yaml under env).

### Extra merger features

Apart from the standard features found in the `PyYaml` library, the `himl-config-merger` component also implements a custom YAML tag called `!include`.

Example:
```yaml
VA7:     !include configs/env=int/region=va7/kafka-brokers.yaml regionBrokers.VA7
```

This will replace the value after interpolation with the value of the regionBrokers.VA7 found under the configs/env=int/region=va7/kafka-brokers.yaml path.

## Custom merge strategy
An optional parameter `type_strategies` can be passed into ConfigProcessor to define custom merging behavior. It could be custom functions that fit your needs.
Your function should take the arguments of (config, path, base, nxt) and return the merged result.

Example:
```py
from himl import ConfigProcessor

def strategy_merge_override(config, path, base, nxt):
    """merge list of dicts. if objects have same id, nxt replaces base."""
    """if remove flag is present in nxt item, remove base and not add nxt"""
    result = deepcopy(base)
    for nxto in nxt:
        for baseo in result:
            # if list is not a list of dicts, bail out and let the next strategy to execute
            if not isinstance(baseo,dict) or not isinstance(nxto,dict):
                return STRATEGY_END
            if 'id' in baseo and 'id' in nxto and baseo['id'] == nxto['id']:
                result.remove(baseo) #same id, remove previous item
        if 'remove' not in nxto:
            result.append(nxto)
    return result

config_processor = ConfigProcessor()
path = "examples/simple/production"
filters = () # can choose to output only specific keys
exclude_keys = () # can choose to remove specific keys
output_format = "yaml" # yaml/json

config_processor.process(path=path, filters=filters, exclude_keys=exclude_keys,
                         output_format=output_format, print_data=True,
                         type_strategies= [(list, [strategy_merge_override,'append']), (dict, ["merge"])] ))

```