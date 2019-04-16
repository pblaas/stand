#!/usr/bin/env python2.7
"""etcd cluster generator."""

import argparse
import os
import subprocess
import base64
import crypt
import string
import random
from jinja2 import Environment, FileSystemLoader

__author__ = "Patrick Blaas <patrick@kite4fun.nl>"
__license__ = "GPL v3"
__version__ = "0.0.2"
__status__ = "Active"

PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ENVIRONMENT = Environment(
    autoescape=False,
    loader=FileSystemLoader(os.path.join(PATH, '.')),
    trim_blocks=True)

# Testing if environment variables are available.
if "OS_USERNAME" not in os.environ:
    os.environ["OS_USERNAME"] = "Default"
if "OS_PASSWORD" not in os.environ:
    os.environ["OS_PASSWORD"] = "Default"
if "OS_TENANT_NAME" not in os.environ:
    os.environ["OS_TENANT_NAME"] = "Default"
if "OS_TENANT_ID" not in os.environ:
    os.environ["OS_TENANT_ID"] = "Default"
if "OS_REGION_NAME" not in os.environ:
    os.environ["OS_REGION_NAME"] = "Default"
if "OS_AUTH_URL" not in os.environ:
    os.environ["OS_AUTH_URL"] = "Default"

parser = argparse.ArgumentParser()
parser.add_argument("keypair", help="Keypair ID")
parser.add_argument("floatingip1", help="Floatingip 1 for API calls")
parser.add_argument("--corepassword", help="Password to authenticate with core user")
parser.add_argument("--username", help="Openstack username - (OS_USERNAME environment variable)", default=os.environ["OS_USERNAME"])
parser.add_argument("--projectname", help="Openstack project Name - (OS_TENANT_NAME environment variable)", default=os.environ["OS_TENANT_NAME"])
parser.add_argument("--clustername", help="Clustername - (standcluster)", default="standcluster")
parser.add_argument("--subnetcidr", help="Private subnet CIDR - (192.168.3.0/24)", default="192.168.3.0/24")
parser.add_argument("--podcidr", help="Pod subnet CIDR - (10.244.0.0/16)", default="10.244.0.0/16")
parser.add_argument("--nodes", help="Number of etcd servers - (3)", type=int, default=3)
parser.add_argument("--imageflavor", help="Manager image flavor ID - (2004)", type=int, default=2004)
parser.add_argument("--glanceimagename", help="Glance image name ID - (Container Linux CoreOS (third-party)", default="Container Linux CoreOS (third-party)")
parser.add_argument("--dnsserver", help="DNS server - (8.8.8.8)", default="8.8.8.8")
parser.add_argument("--etcdver", help="ETCD version - (3.3.12)", default="3.3.12")
parser.add_argument("--flannelver", help="Flannel image version - (0.11.0)", default="0.11.0")
args = parser.parse_args()

template = TEMPLATE_ENVIRONMENT.get_template('etcd.tf.tmpl')
cloudconf_template = TEMPLATE_ENVIRONMENT.get_template('etcdcloudconf.yaml.tmpl')
opensslmanager_template = TEMPLATE_ENVIRONMENT.get_template('./tls/openssl.cnf.tmpl')
clusterstatus_template = TEMPLATE_ENVIRONMENT.get_template('cluster.status.tmpl')

try:
    # Create CA certificates
    def createCaCert():
        """Create CA certificates."""

        print("etcd CA")
        subprocess.call(["openssl", "genrsa", "-out", "etcd-ca-key.pem", "2048"], cwd='./tls')
        subprocess.call(["openssl", "req", "-x509", "-new", "-nodes", "-key", "etcd-ca-key.pem", "-days", "10000", "-out", "etcd-ca.pem", "-subj", "/CN=etcd-ca"], cwd='./tls')

    # Create node certificates
    def createNodeCert(nodeip, k8srole):
        """Create Node certificates."""
        print("received: " + nodeip)
        if k8srole == "manager":
            openssltemplate = (opensslmanager_template.render(
                floatingip1=args.floatingip1,
                ipaddress=nodeip,
                loadbalancer=(args.subnetcidr).rsplit('.', 1)[0] + ".3"
            ))
        else:
            openssltemplate = (opensslworker_template.render(
                ipaddress=nodeip,
            ))

        with open('./tls/openssl.cnf', 'w') as openssl:
            openssl.write(openssltemplate)

        nodeoctet = nodeip.rsplit('.')[3]

        # ${i}-etcd-worker.pem
        subprocess.call(["openssl", "genrsa", "-out", nodeip + "-etcd-node-key.pem", "2048"], cwd='./tls')
        subprocess.call(["openssl", "req", "-new", "-key", nodeip + "-etcd-node-key.pem", "-out", nodeip + "-etcd-node.csr", "-subj", "/CN=" + nodeip + "-etcd-node", "-config", "openssl.cnf"], cwd='./tls')
        subprocess.call(["openssl", "x509", "-req", "-in", nodeip + "-etcd-node.csr", "-CA", "etcd-ca.pem", "-CAkey", "etcd-ca-key.pem", "-CAcreateserial", "-out", nodeip + "-etcd-node.pem", "-days", "365", "-extensions", "v3_req", "-extfile", "openssl.cnf"], cwd='./tls')

    def configTranspiler(nodeip):
        """Create json file from yaml content."""
        subprocess.call(["./ct", "-files-dir=tls", "-in-file", "node_" + nodeip + ".yaml", "-out-file", "node_" + nodeip + ".json", "-pretty"])

    def generatePassword():
        """Generate a random password."""
        randomsalt = ""
        global password
        global cryptedPass
        password = ""
        choices = string.ascii_uppercase + string.digits + string.ascii_lowercase
        for _ in range(0, 12):
            password += random.choice(choices)
        for _ in range(0, 8):
            randomsalt += random.choice(choices)
        cryptedPass = crypt.crypt(password, '$6$%s$' % randomsalt)

    def generateRandomString():
        """Generate a random String."""
        rndstring = ""
        choices = string.ascii_uppercase + string.digits + string.ascii_lowercase
        for _ in range(0, 10):
            rndstring += random.choice(choices)
        return rndstring

    def returnPublicKey():
        """Retrieve rsa-ssh public key from OpenStack."""
        global rsakey
        rsakey = subprocess.check_output(["openstack", "keypair", "show", "--public-key", args.keypair]).strip()
        return rsakey

    def printClusterInfo():
        """Print cluster info."""
        print("-" * 40 + "\n\nCluster Info:")
        print("Clustername:\t" + str(args.clustername))
        print("Glance imgname:\t" + str(args.glanceimagename))
        print("Image flavor:\t" + str(args.imageflavor))
        print("Core password:\t" + str(password))
        print("etcd vers:\t" + str(args.etcdver))
        print("Flannel vers:\t" + str(args.flannelver))
        print("VIP1:\t\t" + str(args.floatingip1))
        print("Cluster cidr:\t" + str(args.subnetcidr))
        print("Pod Cidr:\t" + str(args.podcidr))
        print("Dnsserver:\t" + str(args.dnsserver))
        print("Nodes:\t\t" + str(args.nodes))
        print("Keypair:\t" + str(rsakey))
        print("-" * 40 + "\n")
        print("To start building the cluster: \tterraform init && terraform plan && terraform apply && sh snat_acl.sh")
        print("To interact with the cluster: \tsh kubeconfig.sh")

        clusterstatusconfig_template = (clusterstatus_template.render(
            etcdendpointsurls=iplist.rstrip(','),
            password=password,
            clustername=args.clustername,
            subnetcidr=args.subnetcidr,
            nodes=args.nodes,
            imageflavor=args.imageflavor,
            glanceimagename=args.glanceimagename,
            floatingip1=args.floatingip1,
            dnsserver=args.dnsserver,
            podcidr=args.podcidr,
            flannelver=args.flannelver,
            etcdver=args.etcdver,
            keypair=args.keypair,
            rsakey=rsakey,
        ))

        with open('cluster.status', 'w') as etcdstat:
            etcdstat.write(clusterstatusconfig_template)

    if args.nodes < 3:
        raise Exception('nodes need to be no less then 3.')

    iplist = ""
    for node in range(10, args.nodes + 10):
        apiserver = str("https://" + args.subnetcidr.rsplit('.', 1)[0] + "." + str(node) + ":2379,")
        iplist = iplist + apiserver

    initialclusterlist = ""
    for node in range(10, args.nodes + 10):
        apiserver = str("infra" + str(node - 10) + "=https://" + args.subnetcidr.rsplit('.', 1)[0] + "." + str(node) + ":2380,")
        initialclusterlist = initialclusterlist + apiserver

    createCaCert()
    # Create core user passowrd
    generatePassword()
    returnPublicKey()
    etcdtoken = generateRandomString()

    etcdtemplate = (template.render(
        username=args.username,
        projectname=args.projectname,
        clustername=args.clustername,
        nodes=args.nodes,
        subnetcidr=args.subnetcidr,
        podcidr=args.podcidr,
        keypair=args.keypair,
        imageflavor=args.imageflavor,
        glanceimagename=args.glanceimagename,
        floatingip1=args.floatingip1,
    ))

    for node in range(10, args.nodes + 10):
        lanip = str(args.subnetcidr.rsplit('.', 1)[0] + "." + str(node))
        nodeyaml = str("node_" + lanip.rstrip(' ') + ".yaml")
        createNodeCert(lanip, "manager")

        manager_template = (cloudconf_template.render(
            cryptedPass=cryptedPass,
            sshkey=rsakey,
            nodes=args.nodes,
            dnsserver=args.dnsserver,
            etcdendpointsurls=iplist.rstrip(','),
            etcdid=(node - 10),
            etcdtoken=etcdtoken,
            initialclusterlist=initialclusterlist.rstrip(','),
            floatingip1=args.floatingip1,
            flannelver=args.flannelver,
            etcdver=args.etcdver,
            clustername=args.clustername,
            subnetcidr=args.subnetcidr,
            podcidr=args.podcidr,
            ipaddress=lanip,
            ipaddressgw=(args.subnetcidr).rsplit('.', 1)[0] + ".1"
        ))

        with open(nodeyaml, 'w') as controller:
            controller.write(manager_template)

    for node in range(10, args.nodes + 10):
        lanip = str(args.subnetcidr.rsplit('.', 1)[0] + "." + str(node))
        configTranspiler(lanip)

    with open('etcd.tf', 'w') as etcd:
        etcd.write(etcdtemplate)

except Exception as e:
    raise
else:
    printClusterInfo()
