import os
import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_wpcli_exists(host):
    wpcli = host.file("/usr/local/bin/wp")

    assert wpcli.exists
    assert wpcli.mode == 0o755


def test_download_wordpress(host):
    wpdir = host.file("/var/www/wordpress")

    assert wpdir.exists
    assert wpdir.is_directory

    wpload = host.file("/var/www/wordpress/wp-load.php")

    assert wpload.exists


# def test_wordpress_version(host):
#     version = host.ansible.get_variables()["wordpress_version"]
#     path = str(host.ansible.get_variables()["wordpress_path"])

#     installed = subprocess.check_output("wp --allow-root core version --path=%s".split() % path).strip()  # noqa
#     assert version == installed
