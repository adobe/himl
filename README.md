# himl
A hierarchical config using yaml in Python.

Latest version is: 0.7.1

## Description

A python module which allows you to merge hierarchical config files using YAML syntax. It offers deep merge, variable interpolation and secrets retrieval from secrets managers.

It is ideal if you want to structure your hierarchy in such a way that you avoid duplication. You can define a structure for your configuration using a hierarchy such environment/project/cluster/app. It is up to you what layers you want to use in this hierarchy. The tool will read all yaml files starting from the root (where default values would be) all the way to the leaf (where most specific values would be, which will take precedence).

Idea came from puppet's hiera.

## Table of Contents  

1. [Installation](#installation)
2. [Examples](#examples)
3. [Features](#features)
    * [Interpolation](#feature-interpolation)
    * [Deep merge](#feature-deep-merge)
    * [Secrets retrieval](#feature-secrets-retrieval)
    * [Merge with Terraform remote state](#feature-terraform-remote-state)

<a name="installation"/>

## Installation

### Using `pip`

```sh
pip install himl
```

### From Source

```
git clone https://github.com/adobe/himl
cd himl
sudo python setup.py install
```

<a name="examples"/>

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

<a name="deep-merge-example"/>

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

<a name="features"/>

## Features

<a name="feature-interpolation"/>

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

<a name="feature-deep-merge"/>

### Deep merge

It's possible to have the same key (eg. a dict/list) in multiple files and combine them using a deep merge.
See an example [here](https://github.com/adobe/himl#deep-merge-example).

<a name="feature-secrets-retrieval"/>

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

Not yet implemented.


<a name="feature-terraform-remote-state"/>

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
