import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_hosts_file(host):
    f = host.file('/etc/hosts')

    assert f.exists
    assert f.user == 'root'
    assert f.group == 'root'


def test_wpcli_exists(host):
    wpcli = host.file("/usr/local/bin/wp")

    assert wpcli.exists
    assert wpcli.mode == 0o755


def test_download_wordpress(host):
    wpdir = host.file("/var/www/wordpress")

    assert wpdir.exists
    assert wpdir.is_directory

    wpsettings = host.file("/var/www/wordpress/wp-settings.php")

    assert wpsettings.exists
