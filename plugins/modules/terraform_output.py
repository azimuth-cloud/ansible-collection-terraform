#!/usr/bin/python

# -*- coding: utf-8 -*-
# Code reused from https://github.com/ansible-collections/community.general/blob/main/plugins/modules/cloud/misc/terraform.py
from __future__ import absolute_import, division, print_function

import json
import os

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six.moves import shlex_quote

__metaclass__ = type


DOCUMENTATION = r"""
---
module: terraform_output
short_description: Returns the output of an existing Terraform deployment
description:
     - Provides support for pulling the existing state of Terraform resources
       and exposing the resource information to Ansible.
options:
  binary_path:
    description:
      - The path of a terraform binary to use, relative to the 'service_path'
        unless you supply an absolute path.
    type: path
  project_path:
    description:
      - The path to the root of the Terraform directory with the
        backend configuration.
    type: path
    required: true
  plugin_paths:
    description:
      - List of paths containing Terraform plugin executable files.
      - Plugin executables can be downloaded from U(https://releases.hashicorp.com/).
      - When set, the plugin discovery and auto-download behavior of Terraform is disabled.
      - The directory structure in the plugin path can be tricky. The Terraform docs
        U(https://learn.hashicorp.com/tutorials/terraform/automate-terraform#pre-installed-plugins)
        show a simple directory of files, but actually, the directory structure
        has to follow the same structure you would see if Terraform auto-downloaded the plugins.
        See the examples below for a tree output of an example plugin directory.
    type: list
    elements: path
    version_added: 3.0.0
  workspace:
    description:
      - The terraform workspace to work with.
    type: str
    default: default
  state_file:
    description:
      - The path to an existing Terraform state file to use.
        If this is not specified, the default `terraform.tfstate` will be used.
    type: path
  backend_config:
    description:
      - A group of key-values to provide at init stage to the -backend-config parameter.
    type: dict
  backend_config_files:
    description:
      - The path to a configuration file to provide at init state to the -backend-config parameter.
        This can accept a list of paths to multiple configuration files.
    type: list
    elements: path
    version_added: '0.2.0'
notes:
   - To just run a `terraform plan`, use check mode.
requirements: [ "terraform" ]
author: "Matt Pryor (StackHPC)"
"""

EXAMPLES = """
- name: Read outputs from a previously deployed project
  azimuth_cloud.terraform.terraform_output:
    project_path: "{{ project_dir }}"
"""

RETURN = """
outputs:
  type: complex
  description: A dictionary of all the TF outputs by their assigned name. Use `.outputs.MyOutputName.value` to access the value.
  returned: on success
  sample: '{"bukkit_arn": {"sensitive": false, "type": "string", "value": "arn:aws:s3:::tf-test-bukkit"}'
  contains:
    sensitive:
      type: bool
      returned: always
      description: Whether Terraform has marked this value as sensitive
    type:
      type: str
      returned: always
      description: The type of the value (string, int, etc)
    value:
      type: str
      returned: always
      description: The value of the output as interpolated by Terraform
stdout:
  type: str
  description: Full `terraform` command stdout, in case you want to display it or examine the event log
  returned: always
  sample: ''
command:
  type: str
  description: Full `terraform` command built by this module, in case you want to re-run the command outside the module or debug a problem.
  returned: always
  sample: terraform output ...
"""

module = None


def preflight_validation(bin_path, project_path):
    if project_path is None or "/" not in project_path:
        module.fail_json(msg="Path for Terraform project can not be None or ''.")
    if not os.path.exists(bin_path):
        module.fail_json(
            msg=f"Path for Terraform binary '{bin_path}' doesn't exist on this host - check the path and try again please."
        )
    if not os.path.isdir(project_path):
        module.fail_json(
            msg=f"Path for Terraform project '{project_path}' doesn't exist on this host - check the path and try again please."
        )


def init_plugins(
    bin_path, project_path, backend_config, backend_config_files, plugin_paths
):
    command = [bin_path, "init", "-input=false", "-reconfigure"]
    if backend_config:
        for key, val in backend_config.items():
            command.extend(["-backend-config", shlex_quote(f"{key}={val}")])
    if backend_config_files:
        for f in backend_config_files:
            command.extend(["-backend-config", f])
    if plugin_paths:
        for plugin_path in plugin_paths:
            command.extend(["-plugin-dir", plugin_path])
    _, _, _ = module.run_command(command, check_rc=True, cwd=project_path)


def get_workspace_context(bin_path, project_path):
    workspace_ctx = {"current": "default", "all": []}
    command = [bin_path, "workspace", "list", "-no-color"]
    rc, out, err = module.run_command(command, cwd=project_path)
    if rc != 0:
        module.warn(f"Failed to list Terraform workspaces:\r\n{err}")
    for item in out.split("\n"):
        stripped_item = item.strip()
        if not stripped_item:
            continue
        if stripped_item.startswith("* "):
            workspace_ctx["current"] = stripped_item.replace("* ", "")
        else:
            workspace_ctx["all"].append(stripped_item)
    return workspace_ctx


def select_workspace(bin_path, project_path, workspace):
    command = [bin_path, "workspace", "select", workspace, "-no-color"]
    rc, out, err = module.run_command(command, check_rc=True, cwd=project_path)
    return rc, out, err


def main():
    global module
    module = AnsibleModule(
        argument_spec={
            "project_path": {"required": True, "type": "path"},
            "binary_path": {"type": "path"},
            "plugin_paths": {"type": "list", "elements": "path"},
            "workspace": {"type": "str", "default": "default"},
            "state_file": {"type": "path"},
            "backend_config": {"type": "dict"},
            "backend_config_files": {"type": "list", "elements": "path"},
        },
        supports_check_mode=True,
    )

    project_path = module.params.get("project_path")
    bin_path = module.params.get("binary_path")
    plugin_paths = module.params.get("plugin_paths")
    workspace = module.params.get("workspace")
    state_file = module.params.get("state_file")
    backend_config = module.params.get("backend_config")
    backend_config_files = module.params.get("backend_config_files")

    bin_path = bin_path or module.get_bin_path("terraform", required=True)

    # Always initialise the backend
    init_plugins(
        bin_path, project_path, backend_config, backend_config_files, plugin_paths
    )

    # Check the workspace if required
    workspace_ctx = get_workspace_context(bin_path, project_path)
    if workspace_ctx["current"] != workspace:
        if workspace in workspace_ctx["all"]:
            select_workspace(bin_path, project_path, workspace)
        else:
            module.fail_json(msg=f"Workspace '{workspace}' does not exist.")

    preflight_validation(bin_path, project_path)

    out, err = "", ""
    command = [bin_path, "output", "-no-color", "-json"]
    if state_file and os.path.exists(state_file):
        command.extend(["-state", state_file])
    rc, out, err = module.run_command(command, cwd=project_path)
    if rc == 0:
        outputs = json.loads(out)
    else:
        outputs = {}

    # Restore the Terraform workspace found when running the module
    if workspace_ctx["current"] != workspace:
        select_workspace(bin_path, project_path, workspace_ctx["current"])

    if rc == 0:
        module.exit_json(
            changed=False,
            workspace=workspace,
            outputs=outputs,
            stdout=out,
            stderr=err,
            command=" ".join(command),
        )
    else:
        module.fail_json(
            msg="Failure when getting Terraform outputs.",
            rc=rc,
            stdout=out,
            stdout_lines=out.splitlines(),
            stderr=err,
            stderr_lines=err.splitlines(),
            cmd=" ".join(command),
        )


if __name__ == "__main__":
    main()
