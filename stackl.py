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
  secret_handler:
      description: Name of the secret handler
      required: false
      default: base64
      choices: 
        - vault
        - base64
  vault_addr:
      description: Vault Address
      required: false
  vault_token_path:
      description: Vault token path
      required: false
'''

EXAMPLES = '''
plugin: stackl
host: "http://localhost:8080"
stack_instance: "test_vm"
'''

import json
import hvac
import stackl_client

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin


def get_vault_secrets(service, address, token_path):
    f = open(token_path, "r")
    token = f.readline()
    client = hvac.Client(url=address, token=token)
    secret_dict = {}
    for _, value in service.secrets.items():
        secret_value = client.read(value)
        for key, value in secret_value['data']['data'].items():
            secret_dict[key] = value
    return secret_dict


def get_base64_secrets(service):
    return {}


class InventoryModule(BaseInventoryPlugin):

    NAME = 'stackl'

    def verify_file(self, path):
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
            api_instance = stackl_client.StackInstancesApi(
                api_client=api_client)

            stack_instance_name = self.get_option("stack_instance")
            stack_instance = api_instance.get_stack_instance(
                stack_instance_name)

            for service, si_service in stack_instance.services.items():
                self.inventory.add_group(service)
                self.inventory.set_variable(service, "infrastructure_target",
                                            si_service.infrastructure_target)
                for key, value in si_service.provisioning_parameters.items():
                    self.inventory.set_variable(service, key, value)
                if si_service.hosts is not None:
                    for host in si_service.hosts:
                        self.inventory.add_host(host=host, group=service)
                        self.inventory.set_variable(
                            service, "ansible_user",
                            si_service.connection_credentials.username)
                        self.inventory.set_variable(
                            service, "ansible_password",
                            si_service.connection_credentials.password)
                        self.inventory.set_variable(
                            service, "ansible_become_password",
                            si_service.connection_credentials.password)
                        self.inventory.set_variable(
                            service, "ansible_ssh_common_args",
                            "-o StrictHostKeyChecking=no")

                else:
                    self.inventory.add_host(host="kubernetes-" + service,
                                            group=service)

                if hasattr(si_service, "secrets"):
                    if self.get_option("secret_handler") == "vault":
                        secrets = get_vault_secrets(
                            si_service, self.get_option("vault_addr"),
                            self.get_option("vault_token_path"))
                    elif self.get_option("secret_handler") == "base64":
                        secrets = get_base64_secrets(si_service)
                    for key, value in secrets.items():
                        self.inventory.set_variable(service, key, value)

        except Exception as e:
            raise AnsibleParserError(
                'All correct options required: {}'.format(e))
