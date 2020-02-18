from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
name: stackl
plugin_type: inventory
author:
  - Stef Graces <@stgrace>
short_description: Stackl inventory
description:
  - Fetch a Stack instance from Stackl.
  - Uses a YAML configuration file that ends with C(stackl.(yml|yaml)).
options:
  plugin:
      description: Name of the plugin
      required: true
      choices: ['stackl']
  host:
      description: Stackl's host url
      required: true
  stack_instance:
      description: Stack instance name
      required: true
'''

EXAMPLES = '''
plugin: stackl
host: "http://localhost:8080"
stack_instance: "test_vm"
'''

import json
import stackl_sdk

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin

class InventoryModule(BaseInventoryPlugin):

  NAME = 'stackl'

  def verify_file(self, path):
    ''' return true/false if this is possibly a valid file for this plugin to consume '''
    valid = False
    if super(InventoryModule, self).verify_file(path):
        # base class verifies that file exists and is readable by current user
        if path.endswith(('stackl.yaml', 'stackl.yml')):
            valid = True
    return valid

  def parse(self, inventory, loader, path, cache):
    super(InventoryModule, self).parse(inventory, loader, path, cache)
    self._read_config_data(path)
    try:
      self.plugin = self.get_option('plugin')
      configuration = stackl_sdk.Configuration()
      configuration.host = self.get_option("host")
      api_client = stackl_sdk.ApiClient(configuration=configuration)
      api_instance = stackl_sdk.StackInstancesApi(api_client=api_client)

      stack_instance_name = self.get_option("stack_instance")

      stack_instance = api_instance.get_stack_instance(stack_instance_name)
      self.inventory.add_group(stack_instance_name)
      for service in stack_instance.services.keys():
        self.inventory.add_host(host=service, group=stack_instance_name)
        self.inventory.set_variable(service, "infrastructure_target", 
                                    stack_instance.services[service].infrastructure_target)
        self.inventory.set_variable(service, "provisioning_parameters",
                                    stack_instance.services[service].provisioning_parameters)

    except Exception as e:
      raise AnsibleParserError(
        'All correct options required: {}'.format(e))