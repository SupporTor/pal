from common import conf_get, conf_get_list, puppet_configuration, shell
from time import sleep
import digitalocean
import random
import tempfile

def do_manager():
    return digitalocean.Manager(token=conf_get("digitalocean", "api_key"))

def get_droplet_id(name):
    manager = do_manager()
    droplets = manager.get_all_droplets()
    for droplet in droplets:
        if droplet.name == name:
            return droplet.id
    else:
        raise digitalocean.TokenError("Droplet %s not found" % name) 

def create(name):
    # Setup all the variables needed to complete the request
    image = random.choice(conf_get_list('digitalocean', 'images'))
    region = random.choice(conf_get_list('digitalocean', 'geographies'))
    size = conf_get('digitalocean', 'size') 
    ssh_key_id = conf_get('digitalocean', 'ssh_key_id')
    token = conf_get("digitalocean", "api_key")

    # Get the ssh_key object
    manager = do_manager() 
    ssh_key = manager.get_ssh_key(ssh_key_id) 

    droplet = digitalocean.Droplet(token = token,
                                   name = name,
                                   region = region,
                                   image = image,
                                   size_slug = size,
                                   ssh_keys = [ssh_key])
    droplet.create()
    did = get_droplet_id(name)
    while True:
        actual_droplet = manager.get_droplet(did)
        if actual_droplet.status == 'active':
            break
        sleep(10)

    return {'name': actual_droplet.name}

def destroy(name):
    manager = do_manager()
    did = get_droplet_id(name)
    droplet = manager.get_droplet(did)
    droplet.destroy()

def get_droplet_ip(name):
    manager = do_manager()
    did = get_droplet_id(name)
    droplet = manager.get_droplet(did)
    return droplet.ip_address

def dexec(name, user, command):
    dip = get_droplet_ip(name)
    ssh_base_cmd = "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i ~/.ssh/supporttor_bootstrap %s@%s" % (user, dip)
    return shell('%s \'%s\'' % (ssh_base_cmd, command))
    
def bootstrap(name):
    user = 'freebsd'
    bootstrap_user = "bootstrap"
    pub_key = shell('cat ~/.ssh/supporttor_bootstrap.pub')

    # Add user bootstrap
    dexec(name, user, 'sudo pw useradd -n %s -m -s /bin/sh' % bootstrap_user)

    # Add bootstrap user to sudoers
    dexec(name, user, 'echo "%s ALL=(ALL) NOPASSWD:ALL" | sudo tee -a /usr/local/etc/sudoers' % bootstrap_user)

    # Make .ssh directory in bootstrap home
    dexec(name, user, 'sudo su %s -c "mkdir -p /home/%s/.ssh"' % (bootstrap_user, bootstrap_user))

    # Add bootstrap key to user
    dexec(name, user, 'echo "%s" | sudo su %s -c "tee /home/%s/.ssh/authorized_keys"' % (pub_key, bootstrap_user, bootstrap_user))
 
    # Delete default digital ocean freebsd user
    dexec(name, user, 'sudo pw userdel -n freebsd')

    # Finally, try ssh in with bootstrap user, run uname 
    dexec(name, bootstrap_user, 'uname -a')

    # Install puppet
    dexec(name, bootstrap_user, 'sudo pkg install -y puppet4')

    # Enable puppet at boot
    dexec(name, bootstrap_user, 'sudo sysrc puppet_enable="YES"')

    # Deploy puppet configuration
    dexec(name, bootstrap_user, 'echo "%s" | sudo tee /usr/local/etc/puppet/puppet.conf' % puppet_configuration)

    # Start puppet now
    dexec(name, bootstrap_user, 'sudo service puppet start')
