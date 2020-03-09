from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
name: stackl
plugin_type: inventory
author:
  - Stef Graces <@stgrace>
  - Frederic Van Reet <@GBrawl>
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
import stackl_client

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
      configuration = stackl_client.Configuration()
      configuration.host = self.get_option("host")
      api_client = stackl_client.ApiClient(configuration=configuration)
      api_instance = stackl_client.StackInstancesApi(api_client=api_client)

      stack_instance_name = self.get_option("stack_instance")
      stack_instance = api_instance.get_stack_instance(stack_instance_name)

      for service, si_service in stack_instance.services.items():
        self.inventory.add_group(service)
        self.inventory.set_variable(service, "infrastructure_target", 
                                    si_service.infrastructure_target)
        self.inventory.set_variable(service, "provisioning_parameters",
                                    si_service.provisioning_parameters)
        if si_service.hosts is not None:
          for host in si_service.hosts:
            self.inventory.add_host(host=host, group=service)
            self.inventory.set_variable(service, "ansible_user", si_service.connection_credentials.username)
            self.inventory.set_variable(service, "ansible_password", si_service.connection_credentials.password)
            self.inventory.set_variable(service, "ansible_become_password", si_service.connection_credentials.password)
            self.inventory.set_variable(service, "ansible_ssh_common_args", "-o StrictHostKeyChecking=no")
        else:
          self.inventory.add_host(host="kubernetes-" + service, group=service)                    

    except Exception as e:
      raise AnsibleParserError(
        'All correct options required: {}'.format(e))