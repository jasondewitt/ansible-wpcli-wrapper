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
    - "This module wraps wp-cli with Ansible so you can perform wp-cli actions in Ansbile playbooks without restoring to the shell or command modules. This is the core subcommand, which can be used download or upgrade the WordPress core files"

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

'''

'''
TODO: support most wp core commands from https://developer.wordpress.org/cli/commands/core/
check-update - return true or false, allow for registering variable to determine if an update task in playbook runs
download - pretty much done, maybe more tests
install - combine with multisite-install based off params passed
is-installed - could be nice to pass true/false back to ansible for playbook stuffs
mulsite-convert - ??
multisite-install - combine with install
update - needs tests
update-db - yes
verify-checksums - needs tests
version - function is written in base class, needs refactor to use as both an ansible action and for version checking in other functions
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.wpcli import *

class wpcli_core(wpcli_command):

    def __init__(self, module):
        
        self.module = module
        self.path = module.params["path"]
        self.action = module.params["action"]
        self.version = module.params["version"]
        self.minor = module.params["minor"]
        self.force = module.params["force"]
        self.network = module.params["network"]

        # do i need this?
        self.result = {}


    def do_action(self):
        
        ## distpach action to proper func 
        dispatch = {
            "download": self.core_download,
            "verify": self.verify_checksums,
            "update": self.core_update,

        }

        dispatch[self.action]()


    def core_download(self):
        # download WordPress core
        if not os.path.exists( "%s/wp-load.php" % self.path ):
            if self.module.check_mode:
                self.module.exit_json(changed=True)

            cmd = self.prep_command()
            cmd.extend( "core download".split() )

            if self.version:
                cmd.append("--version=%s" % self.version)

            (rc, out, err) = self.execute_command(cmd)

            if rc != 0 or "Error" in out:
                self.result["stderr"] = err
                self.result["msg"] = "WordPress download failed"
                self.result["command"] = cmd
                self.module.fail_json(**self.result)
            elif "WordPress downloaded" in out:
                self.result["stdout"] = out
                self.result["changed"] = True
                self.module.exit_json(**self.result)
        else:
            if self.module.check_mode:
                self.module.exit_json(changed=False)
            self.result["stdout"] = "Wordpress already exists in %s" % self.path
            self.result["changed"] = False
            self.module.exit_json(**self.result)


    def core_update(self):
        
        current_version = self.get_wp_version()
        latest = self.find_wp_latest()

        if current_version == latest or current_version == self.version:
            self.result["changed"] = False
            self.result["msg"] = "WordPress at %s is already at version %s" % (self.path, current_version)
            self.result["latest"] = latest
            self.result["current_version"] = current_version
            self.module.exit_json(**self.result)

        else:
            # do upgrade
            if self.module.check_mode:
                self.result["changed"] = True
                self.module.exit_json(**self.result)
                    
            cmd = self.prep_command()

            cmd.extend( 'core update'.split() )
            if self.minor:
                ## support --minor flag or not? Maybe always specify specific version string...
                cmd.append( '--minor' )
            
            (rc, out, err) = self.execute_command(cmd)

            if rc == 0 and "WordPress is up to date" in out:
                # WordPress was already at this version
                self.result["changed"] = False
                self.result["stdout"] = out
                self.result["latest"] = latest
                self.result["current_version"] = current_version
                self.module.exit_json(**self.result)
            elif rc == 0 and "WordPress updated successfully" in out:
                self.result["changed"] = True
                self.result["stdout"] = out
                self.module.exit_json(**self.result)
            else:
                self.result['stderr'] = err
                self.result['msg'] = "WordPress update critically failed, is this path a WordPress install?"
                self.module.fail_json(**self.result)


    def verify_checksums(self):

        cmd = self.prep_command()
        cmd.extend( "core verify-checksums".split() )

        (rc, out, err) = self.execute_command(cmd)
        if rc != 0 and "doesn't verify against checksums" in out:
            self.result["changed"] = False
            self.result["msg"] = "WordPress install at %s doesn't verify against checksums" % self.path
            self.result["path"] = self.path
            self.module.exit_json(**self.result)
        elif rc != 0:
            self.result["changed"] = False
            self.result["msg"] = "Error occured verifying checksums in %s" % self.path
            self.result["stderr"] = err
            self.module.fail_json(**self.result)
        elif rc == 0 and "WordPress installation verifies against checksums" in out:
            self.result["changed"] = False
            self.result["msg"] = "Checksum verification successful"
            self.result["stdout"] = out
            self.module.exit_json(**self.result)
        else:
            # something bad happened
            self.result["msg"] = "Critical error verifying WordPress checksums in %s" % self.path
            self.result["stdout"] = out
            self.result["stderr"] = err
            self.module.fail_json(**self.result)


def main():

    arg_spec = wpcli_common_arg_spec()
    arg_spec.update(
        dict(
            action = dict(type='str', required=True, choices=[
                "download",
                "install",
                "update",
                "verify"
            ]),
            version=dict(type="str", required=False, default=None),
            force=dict(type="bool", required=False, default=False),
            network=dict(type="bool", required=False, default=False),
            minor=dict(type="bool", required=False, default=False),
        )
    )

    module = AnsibleModule(
        argument_spec = arg_spec,
        mutually_exclusive=[
            [ 'version', 'minor' ]
        ],
        supports_check_mode=True
    )

    wp = wpcli_core(module)

    if wp.minor and wp.action != "update":
        module.fail_json(fail=True, msg="Only use \"Minor: True\" on Update action")

    wp.do_action()


# import module snippets
if __name__ == '__main__':
    main()