# Protoplaster

Copyright (c) 2022 [Antmicro](https://www.antmicro.com)

An automated framework for platform testing (Hardware and BSPs).

Currently includes tests for:

* I2C
* GPIO
* Camera

## Installation
```bash
pip install git+https://github.com/antmicro/protoplaster.git
```

## Usage

```
usage: protoplaster [-h] [-g GROUP] [--list-groups] [-o OUTPUT] FILE

positional arguments:
  FILE                  	Path to the test yaml description

options:
  -h, --help            	show this help message and exit
  -g GROUP, --group GROUP	Group to execute
  --list-groups         	List possible groups to execute
  -o OUTPUT, --output OUTPUT	A junit-xml style report of the tests results
```

Protoplaster expects a yaml file describing tests as an input. That yaml file should have a specified structure.

```yaml
---
base:                   # A group specifier
  i2c:                  # A module specifier
  - bus: 1              # There can be specified multiple instances of tests in one module
    addresses: [ 0x3c ] # Every test instance should contain needed parameters to initialize the test
  - bus: 2
    addresses: [ 0x50, 0x30 ]
  camera:
  - device: "/dev/video0"
    camera_name: "Camera name"
    driver_name: "Driver name"
  - device: "/dev/video2"
    camera_name: "Camera2 name"
    driver_name: "Driver2 name"
    save_file: "frame.raw"
additional:
  gpio:
  - number: 20
    value: 1
```

### Groups
In the yaml file, there is a way to define different groups of tests to run them for different purposes. In the example yaml file, there are two groups defined: base and additional. Protoplaster when run without a defined group, will execute every test in each group. When the group is specified with a parameter `-g` or `--group`, only tests in the specified group are going to be run. There is a possibility to list existing groups in the yaml file, simply run `protoplaster --list-groups test.yaml`.

## Base modules parameters
Each base module has some parameters that are needed for test initialization. Those parameters describe the tests and are passed to the test class as its attributes.

### I2C
Required parameters:

* `bus` - i2c bus to check
* `addresses` - addresses of that bus that should be detected

### GPIO
Required parameters:

* `number` - number of the gpio pin
* `value` - the value written to that pin

### Cameras
Required parameters:

* `device` - path to the camera device (eg. /dev/video0)
* `camera_name` - expected camera name
* `driver_name` - expected driver name

Optional parameters:

* `save_file` - a path which the tested frame is saved to (the frame is saved only if this parameter is present)

## Writing additional modules
Apart from base modules available in Protoplaster, you can provide your own extended modules. The module should contain a `test.py` file in the root path. That file should contain a test class that is decorated with `ModuleName("")` from `protoplaster.conf.module` package. That decorator tells Protoplaster what the name of the module is. With that information Protoplaster can then correctly initialize the test parameters.

An external module can be added to the test description yaml file with an additional information about the path to that module. The parameter `__path__` should point to where the root of the module. The individual tests run by Protoplaster should be present in the main class in the `test.py` file. The class's name should start with `Test`, and every test's name in that class should also start with `test`. An example of the extended module's test:

```python
from protoplaster.conf.module import ModuleName

@ModuleName("additional_camera")
class TestAdditionalCamera:
    def test_exists(self):
    	assert self.path == "/dev/video0"
```

And a yaml definition:

```yaml
---
base:
  additional_camera:
    __path__: "/home/user/tests/additional_camera"
    tests:
    - path: "/dev/video0"
    - path: "/dev/video1"
```
