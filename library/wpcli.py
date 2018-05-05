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

from ansible.module_utils.basic import AnsibleModule
import os
import json


class wpcli_command(object):

    def __init__(self, module):

        self.module = module
        self.path = module.params["path"]
        self.action = module.params["action"]
        self.version = module.params["version"]
        self.minor = module.params["minor"]
        self.force = module.params["force"]
        self.network = module.params["network"]

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
        if self.version:
            cmd.append( '--version=%s' % self.version )
        if self.force:
            cmd.append( '--force' )
        if self.network:
            cmd.append( '--network' )

        return cmd


    def core_download(self):
        # download WordPress core

        rc = None
        out = ''
        err = ''

        if not os.path.exists( "%s/wp-load.php" % self.path ):
            ## TODO: check if current version matches version parameter
            if self.module.check_mode:
                self.module.exit_json(changed=True)
            cmd = self.prep_command()
            cmd.extend( "core download".split() )

            (rc, out, err) = self.execute_command(cmd)

            vc_cmd = self.prep_command()
            self.verify_checksums()

            return (rc, out, err)
        else:
            if self.module.check_mode:
                self.module.exit_json(changed=False)
            return (None, "WordPress present", "WordPress already downloaded here")


    def core_update(self):
        
        cmd = self.prep_command()

        cmd.extend( 'core update'.split() )
        if self.minor:
            cmd.append( '--minor' )
        
        (rc, out, err) = self.execute_command(cmd)
        self.result['changed'] = out
        if "WordPress updated successfully" in out:
            self.result['changed'] = True
        elif "WordPress is up to date" in out:
            self.result['changed'] = False
        else:
            self.result['stderr'] = err
            self.result['msg'] = "WordPress update critically failed, is this path a WordPress install?"
            self.module.fail_json(**self.result)
        
        self.module.exit_json(**self.result)


    def verify_checksums(self):

        rc = None
        out = ''
        err = ''

        cmd = self.prep_command()
        cmd.extend( "core verify-checksums".split() )

        (rc, out, err) = self.execute_command(cmd)
        ## checksums did not verify, something went wrong, dump out
        if rc != 0:
            self.module.fail_json(fail=True, msg=err)


def main():
    
    module = AnsibleModule(
        argument_spec = dict(
            path=dict(type='str',  required=True),
            action = dict(type='str', required=True, choices=[
                "download",
                "install",
                "plugin",
                "update",
                "verify"
            ]),
            version=dict(type="str", required=False, default=None),
            force=dict(type="bool", required=False, default=False),
            network=dict(type="bool", required=False, default=False),
            minor=dict(type="bool", required=False, default=False),
        ),
        mutually_exclusive=[
            [ 'version', 'minor' ]
        ],
        supports_check_mode=True
    )



    wp = wpcli_command(module)

    rc = None
    out = ''
    err = ''
    result = {}

    ## distpach action to proper func 
    dispatch = {
        "download": wp.core_download,
        "verify": wp.verify_checksums,
        "update": wp.core_update,

    }

    if wp.minor and wp.action != "update":
        module.fail_json(fail=True, msg="Only use \"Minor: True\" on Update action")

    (rc, out, err) = dispatch[wp.action]()

    if rc is None:
        wp.result['changed'] = False
    else:
        wp.result['changed'] = True
    if out:
        wp.result['stdout'] = out
    if err:
        wp.result['stderr'] = err

    module.exit_json(**wp.result)


# import module snippets
if __name__ == '__main__':
    main()