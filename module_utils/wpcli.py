#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: wpcli

short_description: Wrapper around wp-cli for great WordPress

version_added: 2.5

description:
    - "This module wraps wp-cli with Ansible so you can perform wp-cli actions in Ansbile playbooks without restoring to the shell or command modules"

options:
    path: path to the WordPress installtion to operate on


author:
    - Jason DeWitt (@jasondewitt)
'''

EXAMPLES = '''
# download wordpress core
- name: download WordPress to the specified path
  wpcli:
    path: /path/to/wordpress

'''

import os
from ansible.module_utils.urls import *
try:
    import json
except ImportError:
    import simplejson as json

def wpcli_common_arg_spec():

    arg_spec = dict(
        path=dict(type='str',  required=True),
        force=dict(type='str', required=False),
        network=dict(type='str', required=False),
    )

    return arg_spec


class wpcli_command(object):

    def __init__(self, module):

        self.module = module
        self.path = module.params["path"]
        self.force = module.params["force"]
        self.result = {}


    def execute_command(self, cmd, use_unsafe_shell=False, data=None, obey_checkmode=True):
        if self.module.check_mode and obey_checkmode:
            self.module.debug('In check mode, would have run: "%s"' % cmd)
            return (0, '', '')
        else:
            # cast all args to strings ansible-modules-core/issues/4397
            cmd = [str(x) for x in cmd]
            return self.module.run_command(cmd, use_unsafe_shell=use_unsafe_shell, data=data)

    def prep_command(self):
        cmd = [ self.module.get_bin_path('wp', True) ]
        if os.geteuid()==0:
            cmd.append('--allow-root')
        # always going to want --path on the command, so go ahead and append it now
        cmd.append( '--path=%s' % self.path )
        if self.force:
            cmd.append( '--force' )


        return cmd
    
    def find_wp_versions(self):
        apiurl = "https://api.wordpress.org/core/stable-check/1.0/"

        try:
            versions = json.load(open_url(apiurl))
        except HTTPError as e:
            res = json.load(e)
            self.result["msg"] = "Critical error checking WordPress versions api"
            self.result["stderr"] = res["message"]
            self.module.fail_json(**self.result)
        self.wp_versions = versions


    def find_wp_latest(self):

        try:
            return [key for key in self.wp_versions.keys() if (self.wp_versions[key] == "latest")][0]
        except AttributeError:
            self.find_wp_versions()
            return [key for key in self.wp_versions.keys() if (self.wp_versions[key] == "latest")][0]


    def get_wp_version(self):
        cmd = self.prep_command()
        cmd.extend("core version".split())

        (rc, out, err) = self.execute_command(cmd)
        if rc == 0:
            return out.strip()
        else:
            self.result["msg"] = "%s is not a WordPress install" % self.path
            self.result["stderr"] = err
            self.result["stdout"] = out
            self.module.fail_json(**self.result)


    def is_installed(self):
        cmd = self.prep_command()
        cmd.extend("core is-installed".split())

        (rc, out, err) = self.execute_command(cmd)
        if rc == 0:
            return True
        else:
            return False

