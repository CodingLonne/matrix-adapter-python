## Description
This project defines a *Python* implementation of a plugin adapter for the Synapse server from the chat application Matrix (SUT). 
It allows for communication between the Axini Modeling Platform (AMP) and the Matrix server, Synapse (SUT).

See https://github/axini and the plugin-adapter-protocol repository for some general information on Axini's plugin adapter protocol. Axini's training on "plugin adapters" provides additional and more detailed information.

The software is distributed under the MIT license, see LICENSE.

## Running the adapter
### Prerequisites
This example adapter is depended on Python (>= 3.11) and uses `pip` for its dependency management. The steps below presume that the `python` and `pip` commands are resolvable in your shell.

### Setting it up
- Clone this repository.
- Open a terminal or command prompt.
- (OPTIONAL) Create a separate virtual environment and activate it `python -m venv <name_of_virtual_env_dir>` and `source <name_of_virtual_env_dir>/bin/activate`
- Perform `pip install -r ./requirements.txt`. This should download all the required dependencies.

### Starting the adapter
- Open a terminal or command prompt.
- Run `python src/adapter/plugin_adapter.py -u <adapter url of AMP> -t <authentication token needed by AMP>`.
The relevant adapter url and authentication token are mentioned in the report.

### Running the tests
- While the Adapter is running, go to the axini platform and run the .aml code added in the attachments.

## Some notes on the implementation
Aside from fixing some errors in the library, we only changed the `matrix/handler.py` and removed the smartdoor connection file. We were able to remove this file, since matrix works with the requests library and thus has no need to establish a permanent connection.