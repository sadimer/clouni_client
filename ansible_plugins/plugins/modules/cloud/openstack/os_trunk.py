#!/usr/bin/python3

# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: os_trunk
short_description: Add/Update/Delete ports from an OpenStack cloud.
extends_documentation_fragment: openstack
author: "Roman Stolyarov (Sadimer)"
version_added: "2.0"
description:
   - Add, Update or Remove trunks in OpenStack cloud. A I(state) of
     'present' will ensure the trunk is created or updated if required.
options:
   name:
     description:
        - Name or id that has to be given to the trunk.
   port:
     description:
        - Port ID or name this port belongs to.
     required: true
   sub_ports:
     description:
        - List of dicts with port IDs or names of trunk subports.
     required: false
   state:
     description:
       - Should the resource be present or absent.
     choices: [present, absent]
     default: present
   availability_zone:
     description:
       - Ignored. Present for backwards compatibility
'''

RETURN = '''
id:
    description: Unique UUID.
    returned: success
    type: str
name:
    description: Name given to the trunk.
    returned: success
    type: str
port_id:
    description: Port ID of this trunk.
    returned: success
    type: str
status:
    description: Trunk's status.
    returned: success
    type: str
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.openstack import openstack_full_argument_spec, openstack_module_kwargs, openstack_cloud_from_module


def _needs_update(module, trunk, cloud):
    if module.params['sub_ports'] is not None and trunk.get('sub_ports') is None:
        return True
    if module.params['sub_ports'] is None and trunk.get('sub_ports') is not None:
        return True
    if len(module.params['sub_ports']) != len(trunk.get('sub_ports')):
        return True
    return False


def _get_subports(module, trunk, cloud):
    if module.params['sub_ports'] is not None and trunk['sub_ports'] is None:
        trunk['sub_ports'] = []
    if module.params['sub_ports'] is None and trunk['sub_ports'] is not None:
        module.params['sub_ports'] = []
    new_subports = []
    subports = []
    for elem in module.params['sub_ports']:
        new_subports.append(elem['port_id'])
    for elem in trunk.get('sub_ports'):
        subports.append(elem['port_id'])
    subports_for_create = []
    for port in module.params['sub_ports']:
        for elem in list(set(new_subports).difference(set(subports))):
            if port['port_id'] == elem:
                subports_for_create.append(port)
    subports_for_delete = []
    for port in trunk.get('sub_ports'):
        for elem in list(set(subports).difference(set(new_subports))):
            if port['port_id'] == elem:
                subports_for_delete.append(port)
    return subports_for_create, subports_for_delete

def _system_state_change(module, trunk, cloud):
    state = module.params['state']
    if state == 'present':
        if not trunk:
            return True
        return _needs_update(module, trunk, cloud)
    if state == 'absent' and trunk:
        return True
    return False


def _compose_trunk_args(module, cloud):
    trunk_kwargs = {}
    optional_parameters = ['sub_ports']
    for optional_param in optional_parameters:
        if module.params[optional_param] is not None:
            trunk_kwargs[optional_param] = module.params[optional_param]

    return trunk_kwargs

def main():
    argument_spec = openstack_full_argument_spec(
        name=dict(required=False),
        port=dict(required=False),
        state=dict(default='present', choices=['absent', 'present']),
        sub_ports=dict(type='list', required=False),
    )
    module = AnsibleModule(argument_spec, supports_check_mode=True)

    name = module.params['name']
    state = module.params['state']
    port = module.params['port']

    sdk, cloud = openstack_cloud_from_module(module)

    try:
        trunk = None
        if name:
            trunk = cloud.network.find_trunk(name)
        if module.check_mode:
            module.exit_json(changed=_system_state_change(module, trunk, cloud))

        if not trunk and not port and state == 'present':
            module.fail_json(
                msg="Parameter 'port' is required in Trunk Create"
            )
        if port:
            port = cloud.get_port(port)
        changed = False
        result = {}

        kwargs = _compose_trunk_args(module, cloud)

        if state == 'present':
            if trunk:
                if _needs_update(module, trunk, cloud):
                    subports_for_create, subports_for_delete = _get_subports(module, trunk, cloud)
                    result = cloud.network.add_trunk_subports(trunk, subports_for_create)
                    result = cloud.network.delete_trunk_subports(trunk, subports_for_delete)
                    changed = True
                else:
                    result['trunk'] = trunk
                    result['id'] = trunk['id']
            else:
                if module.params['sub_ports'] is None:
                    module.params['sub_ports'] = []
                if name:
                    args = {'port_id': port['id'], 'name': name, 'sub_ports': module.params['sub_ports']}
                else:
                    args = {'port_id': port['id'], 'sub_ports': module.params['sub_ports']}
                result = cloud.network.create_trunk(**args)
                changed = True
            module.exit_json(changed=changed, id=result['id'], trunk=result)
        if state == 'absent':
            if trunk:
                result = cloud.network.delete_trunk(trunk)
                changed = True
            module.exit_json(changed=changed)
    except sdk.exceptions.OpenStackCloudException as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()
