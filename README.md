# Overview

This project contains a small script, which can be used to easily backup all EBS
volumes attached to especially tagged EC2 instances.

Instances to backup are selected by a configured tag, so the instances to backup
can be easily selected by adding or removing the appropriate tag to the EC2
instance, without any configuration change needed for the script itself.

There is no configuration how long snapshots are kept. Instead it can be
configured how many snapshots of a volume are kept. If more snapshots exist the
oldest ones will be deleted until the maximum amount of desired snapshots has
been reached.


# Usage

```
john@doe:~$ ./ebs_snapshot_automation.py --help
usage: ebs_snapshot_automation.py [-h] -a AWS_ACCESS_KEY -s AWS_SECRET_KEY
                                  [-r REGION] [-n NUM_BACKUPS] [-t TAG]

Script to automate snapshotting of EBS volumes

optional arguments:
  -h, --help            show this help message and exit
  -a AWS_ACCESS_KEY, --access-key AWS_ACCESS_KEY
                        The AWS access key to use
  -s AWS_SECRET_KEY, --secret-key AWS_SECRET_KEY
                        The AWS secret key to use
  -r REGION, --region REGION
                        The AWS region to connect to
  -n NUM_BACKUPS, --num-backups NUM_BACKUPS
                        The number of backups for each volume to keep
  -t TAG, --tag TAG     Key and value (separated by a colon) of a tag attached
                        to instances whose EBS volumes should be backed up
```

# Contribution

Pull Requests are welcome!
