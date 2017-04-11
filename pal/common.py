import ConfigParser
import os
import subprocess

puppet_configuration="""[main]
server = %s 
environment = production
runinterval = 1h
""" % (conf_get('puppet','puppetmaster'))

def shell(command):
    """ Execute a command on the host system """
    try:
        process = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError:
        raise
    return process

def conf_get(section, key):
    fp = os.path.join("/usr/local/etc/supportor/supportor.conf")
    Config = ConfigParser.ConfigParser()
    Config.read(fp)
    return Config.get(section, key)

def conf_get_list(section, key):
    return conf_get(section, key).split(',')
