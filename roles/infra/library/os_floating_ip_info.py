#!/usr/bin/python

# Copyright (c) 2019 STFC.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: os_floating_ip_info
short_description: Returns info about a floating IP.
version_added: "1.0"
author: "Matt Pryor"
description:
  - Return information about the given floating IP.
requirements:
  - "python >= 2.7"
  - "openstacksdk"
options:
  floating_ip:
    type: str
    description:
      - The id of the floating IP to return information about.
    required: true
extends_documentation_fragment: openstack
'''

EXAMPLES = '''
- name: Get info about a floating IP
  os_floating_ip_info:
    floating_ip: <uuid>
  register: result
'''

RETURN = '''
fip_id:
    description: The ID of the floating IP.
    returned: success
    type: str
fip_ip:
    description: The IP address of the floating IP.
    returned: success
    type: str
'''

import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import (
    openstack_full_argument_spec,
    openstack_module_kwargs,
    openstack_cloud_from_module
)


def main():
    argument_spec = openstack_full_argument_spec(
        floating_ip = dict(required=True, type='str'),
    )
    module_kwargs = openstack_module_kwargs()
    module = AnsibleModule(argument_spec, **module_kwargs)

    sdk, cloud = openstack_cloud_from_module(module)
    try:
        sdk_ip = cloud.network.get_ip(module.params['floating_ip'])
        module.exit_json(changed = False, floating_ip = sdk_ip)
    except Exception as e:
        module.fail_json(msg=str(e), exception=traceback.format_exc())


if __name__ == '__main__':
    main()
