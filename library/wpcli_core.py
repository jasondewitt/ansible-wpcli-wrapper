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
import re

class wpcli_core(wpcli_command):

    def __init__(self, module):
        
        self.module = module
        self.path = module.params["path"]
        self.action = module.params["action"]
        self.version = module.params["version"]
        self.minor = module.params["minor"]
        self.force = module.params["force"]
        self.network = module.params["network"]
        self.url = module.params["url"]
        self.title = module.params["title"]
        self.admin_user = module.params["admin_user"]
        self.admin_password = module.params["admin_password"]
        self.admin_email = module.params["admin_email"]
        self.skip_email = module.params["skip_email"]

        # do i need this?
        self.result = {}


    def do_action(self):
        
        ## distpach action to proper func 
        dispatch = {
            "download": self.core_download,
            "verify": self.verify_checksums,
            "update": self.core_update,
            "install": self.core_install

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


    def core_install(self):
        
        if self.is_installed():
            self.result["changed"] = False
            self.result["msg"] = "WordPress at %s is already installed" % (self.path)
            self.module.exit_json(**self.result)
        else:
            
            if self.module.check_mode:
                self.module.exit_json(changed=True)
            
            cmd = self.prep_command()
            cmd.extend("core install".split())

            # required params
            cmd.append("--url=%s" % self.url)
            cmd.append("--title=%s" % self.title)
            cmd.append("--admin_user=%s" % self.admin_user)
            cmd.append("--admin_email=%s" % self.admin_email)

            if self.admin_password:
                cmd.append("--admin_password=%s" % self.admin_password)
            if self.skip_email:
                cmd.append("--skip_email")

            (rc, out, err) = self.execute_command(cmd)

            if "Parameter Error" in out:
                self.result["stderr"] = err
                self.result["msg"] = "Parameter error!"
                self.result["command"] = cmd
                self.module.fail_json(**self.result)
            elif rc != 0:
                self.result["stderr"] = err
                self.result["msg"] = "Error installing WordPress, check generated wp-cli command"
                self.result["command"] = cmd
                self.module.fail_json(**self.result)
            elif rc == 0 and self.is_installed():
                if not self.skip_email and not self.admin_password:
                    m = re.match("^Admin password:\s(.+)\n", out)
                    if m:
                        self.result["admin_password"] = m.group(1)
                self.result["stdout"] = "WordPress sucessfully installed"
                self.result["changed"] = True
                self.module.exit_json(**self.result)



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
                "verify",
                "install"
            ]),
            version=dict(type="str", required=False, default=None),
            force=dict(type="bool", required=False, default=False),
            network=dict(type="bool", required=False, default=False),
            minor=dict(type="bool", required=False, default=False),
            url=dict(type="str", required=False, default=None),
            title=dict(type="str", required=False, default=None),
            admin_user=dict(type="str", required=False, default=None),
            admin_password=dict(type="str", required=False, default=None, no_log=True),
            admin_email=dict(type="str", required=False, default=None),
            skip_email=dict(type="bool", required=False, default=False)
        )
    )

    module = AnsibleModule(
        argument_spec = arg_spec,
        required_if=[
            [ "action", "install", [ "url", "title", "admin_user", "admin_email" ] ]
        ],
        mutually_exclusive=[
            [ 'version', 'minor' ]
        ],
        supports_check_mode=True
    )

    wp = wpcli_core(module)

    if wp.minor and wp.action != "update":
        module.fail_json(fail=True, msg="Only use \"Minor: True\" on Update action")

    if (wp.url or wp.title or wp.admin_user or wp.admin_password or wp.admin_email or wp.skip_email) and wp.action != "install":
        module.fail_json(fail=True, msg="Extraneous options for %s" % wp.action)

    wp.do_action()


# import module snippets
if __name__ == '__main__':
    main()