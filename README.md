[![Build Status](https://travis-ci.org/jasondewitt/ansible-wpcli-wrapper.svg?branch=master)](https://travis-ci.org/jasondewitt/ansible-wpcli-wrapper)

ansible-wpcli-wrapper
=========

WP-CLI is great for managing WordPress from the commandline, and it works resonably well in conjuction with Ansible whe using the shell or command modules. This role and moduleimplement an Ansible native interface for WP-CLI for use in your playbooks.

Requirements
------------

The module requires wp-cli and php to be installed the target host. The role includes a dependency on [mychiara.wp-cli](https://galaxy.ansible.com/mychiara/wp-cli/). I chose this role because it does not depend on a specific PHP role, I dont want this module/role to make any assumptions on how PHP is installed on the target servers, only rely on the fact that is there. Some commands, such as `config` may require the mysql client be installed on the target host.

Module Description
------------------

WP-CLI functionality is broken up into several custom python modules in this role, closely mirrioring the [command structure](https://developer.wordpress.org/cli/commands/) of WP-CLI itself. The intention is to support all of the WP-CLI commands that make sense for running via Ansbile, and some commands may be combined into a single to better fit the Ansible workflow.

Parameters
--------------
Every sub-command that the modules support will require a `path:` parameter, this identifies the WordPress install on the target host to work on, and an `action:` paramter to determine which sub-command of the particular WP-CLI command is run. Each sub-module (core, config, plugin) will have it's own set of paramters and requirements.

Example Playbook
----------------

    - hosts: servers
      roles:
         - { role: ansible-wpcli-wrapper }
      tasks:
        - name: download WordPress
          wpcli_core:
            path: /var/www/wordpress
            action: download
            version: 4.9.5


