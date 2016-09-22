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

# Installation

* Clone this repository and enter the directory you cloned it into.

* Install the script using pip: ```pip install .```

* If the script isn't available in your PATH afterwards, the location where `pip`
installed it into, might not be in your `$PATH`. Try
```export PATH=$PATH:~/.local/bin```

# Usage

```
john@doe:~$ ./ebs_snapshot_automation.py --help
usage: ebs_snapshot_automation.py [-h] [--aws-access-key-id AWS_ACCESS_KEY_ID]
                                  [--aws-secret-access-key AWS_SECRET_ACCESS_KEY]
                                  [--profile PROFILE_NAME]
                                  [--region REGION_NAME] [-n NUM_BACKUPS]
                                  [-t TAG]

Script to automate snapshotting of EBS volumes

optional arguments:
  -h, --help            show this help message and exit
  --aws-access-key-id AWS_ACCESS_KEY_ID
                        Specify a value here if you want to use a different
                        AWS_ACCESS_KEY_ID than configured in the AWS CLI.
  --aws-secret-access-key AWS_SECRET_ACCESS_KEY
                        Specify a value here if you want to use a different
                        AWS_SECRET_ACCESS_KEY than configured in the AWS CLI.
  --profile PROFILE_NAME
                        The AWS CLI profile to use. Defaults to the default
                        profile.
  --region REGION_NAME  The AWS region to connect to. Defaults to the one
                        configured for the AWS CLI.
  -n NUM_BACKUPS, --num-backups NUM_BACKUPS
                        The number of backups for each volume to keep
  -t TAG, --tag TAG     Key and value (separated by a colon) of a tag attached
                        to instances whose EBS volumes should be backed up
```

# Contribution

Pull Requests are welcome!
