# stand
Stand is a project to generate CloudLinux configs and terraform files to bootstrap a HA etcd cluster with with flannel support on top of OpenStack.


### Usage:
```
usage: stand.py [-h] [--corepassword COREPASSWORD] [--username USERNAME]
                [--projectname PROJECTNAME] [--clustername CLUSTERNAME]
                [--subnetcidr SUBNETCIDR] [--podcidr PODCIDR] [--nodes NODES]
                [--imageflavor IMAGEFLAVOR]
                [--glanceimagename GLANCEIMAGENAME] [--dnsserver DNSSERVER]
                [--etcdver ETCDVER] [--flannelver FLANNELVER]
                keypair floatingip1

positional arguments:
  keypair               Keypair ID
  floatingip1           Floatingip 1 for API calls

optional arguments:
  -h, --help            show this help message and exit
  --corepassword COREPASSWORD
                        Password to authenticate with core user
  --username USERNAME   Openstack username - (OS_USERNAME environment
                        variable)
  --projectname PROJECTNAME
                        Openstack project Name - (OS_TENANT_NAME environment
                        variable)
  --clustername CLUSTERNAME
                        Clustername - (standcluster)
  --subnetcidr SUBNETCIDR
                        Private subnet CIDR - (192.168.3.0/24)
  --podcidr PODCIDR     Pod subnet CIDR - (10.244.0.0/16)
  --nodes NODES         Number of etcd servers - (3)
  --imageflavor IMAGEFLAVOR
                        Manager image flavor ID - (2004)
  --glanceimagename GLANCEIMAGENAME
                        Glance image name ID - (Container Linux CoreOS (third-
                        party)
  --dnsserver DNSSERVER
                        DNS server - (8.8.8.8)
  --etcdver ETCDVER     ETCD version - (3.3.1)
  --flannelver FLANNELVER
                        Flannel image version - (0.10.0)
```