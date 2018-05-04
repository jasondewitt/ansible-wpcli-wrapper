#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
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

class wpcli_command(object):

    def __init__(self, module):

        self.module = module
        self.path = module.params["path"]
        self.action = module.params["action"]


    def execute_command(self, cmd, use_unsafe_shell=False, data=None, obey_checkmode=True):
        if self.module.check_mode and obey_checkmode:
            self.module.debug('In check mode, would have run: "%s"' % cmd)
            return (0, '', '')
        else:
            # cast all args to strings ansible-modules-core/issues/4397
            cmd = [str(x) for x in cmd]
            return self.module.run_command(cmd, use_unsafe_shell=use_unsafe_shell, data=data)

    def run_action(self):
        
        cmd = [ self.module.get_bin_path('wp', True) ]
        ## TODO: detect if running as root or not and append this as necessary
        cmd.append('--allow-root')
        # always going to want --path on the command, so go ahead and append it now
        cmd.append( '--path=%s' % self.path )

        if self.action == "download":
            cmd.append( 'core' )
            cmd.append( 'download' )

        ## does this go here?
        if self.module.check_mode:
            self.module.exit_json(changed=True)
        return self.execute_command(cmd)


def main():
    
    module = AnsibleModule(
        argument_spec = dict(
            path=dict(type='str',  required=True),
            action = dict(type='str', required=True, choices=["download", "install", "plugin" ]),
        ),
        supports_check_mode=True
    )

    wp = wpcli_command(module)

    rc = None
    out = ''
    err = ''
    result = {}

    (rc, out, err) = wp.run_action()

    if rc is None:
        result['changed'] = False
    else:
        result['changed'] = True
    if out:
        result['stdout'] = out
    if err:
        result['stderr'] = err

    module.exit_json(**result)


# import module snippets
if __name__ == '__main__':
    main()