#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: wpcli_config

short_description: Wrapper around wp-cli for great WordPress, config subcommand

version_added: 2.5

description:
    - "This module wraps wp-cli with Ansible so you can perform wp-cli actions in Ansbile playbooks without restoring to the shell or command modules. This is the config subcommand, which can be used to create/modify the wp-config.php file"

options:
    path: path to the WordPress installtion to operate on


author:
    - Jason DeWitt (@jasondewitt)
'''

EXAMPLES = '''
# download wordpress core
- name: download WordPress to the specified path
  wpcli_config:
    path: /path/to/wordpress
    action: create
    dbname: wp
    dbuser: wp
    dbpass: password

'''

'''
TODO: support the rest of wp config commands https://developer.wordpress.org/cli/commands/config/
    create - done
    delete - do I really want this?
    get
    has
    list - could be nice
    path - might not be needed, could be good for some playbooks
    set
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.wpcli import *
import os

class wpcli_config(wpcli_command):

    def __init__(self, module):
        
        super(wpcli_config, self).__init__(module)
        
        self.action = module.params["action"]
        self.dbname = module.params["dbname"]
        self.dbuser = module.params["dbuser"]
        self.dbpass = module.params["dbpass"]
        self.dbhost = module.params["dbhost"]
        self.dbprefix = module.params["dbprefix"]
        self.dbcharset = module.params["dbcharset"]
        self.dbcollate = module.params["dbcollate"]
        self.locale = module.params["locale"]

    
    def do_action(self):
        
        dispatch = {
            "create": self.config_create,
    
        }

        dispatch[self.action]()


    def config_create(self):
        
        if os.path.exists("%s/wp-config.php" % self.path):
            if self.module.check_mode:
                self.result["changed"] = False
                self.module.exit_json(**self.result)
            self.result["changed"] = False
            self.result["out"] = "wp-config.php already exists"
            self.module.exit_json(**self.result)
        elif self.module.check_mode:
            self.result["changed"] = True
            self.module.exit_json(**self.result)
        
        cmd = self.prep_command()
        cmd.extend("config create".split())

        cmd.append("--dbname=%s" % self.dbname)
        cmd.append("--dbuser=%s" % self.dbuser)
        cmd.append("--dbpass=%s" % self.dbpass)
        if not self.dbhost:
            cmd.append("--dbhost=localhost")
        else:
            cmd.append("--dbhost=%s" % self.dbhost)
        if self.dbprefix:
            cmd.append("--dbprefix=%s" % self.dbprefix)
        if self.dbcharset:
            cmd.append("--dbcharset=%s" % self.dbcharset)
        if self.dbcollate:
            cmd.append("--dbcollate=%s" % self.dbcollate)
        if self.locale:
            cmd.append("--locale=%s" % self.locale)
        
        (rc, out, err) = self.execute_command(cmd)

        if rc != 0 or "Error" in out:
            self.result["stderr"] = err
            self.result["msg"] = "wp-config.php file creation failed"
            self.result["command"] = cmd
            self.module.fail_json(**self.result)
        elif os.path.exists("%s/wp-config.php" % self.path):
            self.result["out"] = "wp-config.php created sucessfully"
            self.result["changed"] = True
            self.module.exit_json(**self.result)


def main():
    
    arg_spec = wpcli_common_arg_spec()
    arg_spec.update(
        dict(
            action = dict(type='str', required=True, choices=[
                "create",

            ]),
            dbname=dict(type='str', required=False),
            dbuser=dict(type='str', required=False),
            dbpass=dict(type='str', required=False),
            dbhost=dict(type='str', required=False),
            dbprefix=dict(type='str', required=False),
            dbcharset=dict(type='str', required=False),
            dbcollate=dict(type='str', required=False),
            locale=dict(type='str', required=False),
        )
    )

    module = AnsibleModule(
        argument_spec = arg_spec,
        required_if=[
            [ "action", "create", [ "dbname", "dbuser", "dbpass" ] ]
        ],
        supports_check_mode=True
    )

    wp = wpcli_config(module)

    wp.do_action()



# import module snippets
if __name__ == '__main__':
    main()