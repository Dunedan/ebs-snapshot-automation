#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel Roschka <daniel@smaato.com>
Copyright: Smaato Inc. 2014-2016
URL: https://github.com/smaato/ebs-snapshot-automation

A small script meant to be run as a cronjob to regularly snapshot EBS volumes
attached to EC2 instances and handle rolling backups for these snapshots.

Instances to backup are selected by a configured tag, so the instances to
backup can be easily selected by adding or removing the appropriate tag to the
EC2 instance, without any configuration change needed for this script.
"""

import argparse
import logging
import sys
from datetime import datetime
from itertools import chain

from boto3.session import Session
from botocore.exceptions import BotoCoreError


def make_snapshots(client, tag_key, tag_value):
    """Create snapshots.

    Create a snapshot for every EBS volume attached to an instance which
    contains the tag used to filter for instances to backup.
    """
    tag_filter = {'Name': 'tag:%s' % tag_key, 'Values': [tag_value]}
    try:
        reservations = client.describe_instances(Filters=[tag_filter])['Reservations']
    except BotoCoreError as exc:
        logging.error("Failed to get list of instances to back up:\n%s", exc)
    instances = list(chain.from_iterable([x['Instances'] for x in reservations]))
    if not instances:
        logging.warning("Couldn't find any instances whose volumes need snapshotting. Aborting …")
        sys.exit(0)

    # Create snapshots for all volumes per instance.
    for instance in instances:
        # Get the volumes attached to the instance.
        try:
            volumes_for_instance = client.describe_volumes(Filters=[
                {'Name': 'attachment.instance-id',
                 'Values': [instance['InstanceId']]},
                {'Name': 'status',
                 'Values': ['in-use']}])['Volumes']
        except BotoCoreError as exc:
            logging.error("Failed to get the list of volumes attached to instance %s:\n%s",
                          instance['InstanceId'], exc)
        if not volumes_for_instance:
            logging.warning("Found instance %s to backup, but no attached "
                            "volumes. Something is fishy here. Aborting …",
                            instance['InstanceId'])
            sys.exit(1)

        # Get the instance name from the tags if it exists.
        instance_name = None
        for tag in instance['Tags']:
            if tag['Key'] == 'Name':
                instance_name = tag['Value']
                continue

        for volume in volumes_for_instance:
            attachments = volume['Attachments']
            volume_attach_devices = ', '.join([att['Device'] for att in attachments])
            volume_attach_instances = ', '.join([att['InstanceId'] for att in attachments])

            if instance_name:
                description = ('automated snapshot of volume '
                               '%s attached as %s to %s (%s)' %
                               (volume['VolumeId'],
                                volume_attach_devices,
                                instance_name,
                                volume_attach_instances))
            else:
                description = ('automated snapshot of volume '
                               '%s attached as %s to %s' %
                               (volume['VolumeId'],
                                volume_attach_devices,
                                volume_attach_instances))
            try:
                snapshot = client.create_snapshot(VolumeId=volume['VolumeId'],
                                                  Description=description)
            except BotoCoreError as exc:
                logging.error("Creating a snapshot of volume %s failed:\n%s",
                              volume['VolumeId'],
                              exc)
            else:
                logging.info("Creating snapshot %s of volume %s",
                             snapshot['SnapshotId'],
                             volume['VolumeId'])
            snapshot_date = datetime.now().strftime('%Y-%m-%d %H:%M')
            if instance_name:
                name_tag_value = '%s %s %s' % (instance_name,
                                               volume_attach_devices,
                                               snapshot_date)
            else:
                name_tag_value = '%s %s %s' % (volume_attach_instances,
                                               volume_attach_devices,
                                               snapshot_date)
            try:
                client.create_tags(Resources=[snapshot['SnapshotId']],
                                   Tags=[{'Key': 'Name',
                                          'Value': name_tag_value},
                                         {'Key': 'Creator',
                                          'Value': 'ebs_snapshot_automation'},
                                         {'Key': 'Origin-Instance',
                                          'Value': instance['InstanceId']},
                                         {'Key': 'Origin-%s' % tag_key,
                                          'Value': tag_value}])
            except BotoCoreError as exc:
                logging.error("Tagging the snapshot %s of volume %s failed:\n%s",
                              snapshot['SnapshotId'],
                              volume['VolumeId'],
                              exc)


def delete_old_snapshots(client, tag_key, tag_value, num_backups):
    """Remove old snapshots.

    Remove the oldest snapshots for a volume, which have been made for the
    specified tag, if there are more snapshots than configured in num_backups.
    """
    try:
        snapshots = client.describe_snapshots(Filters=[
            {'Name': 'tag:Creator', 'Values': ['ebs_snapshot_automation']},
            {'Name': 'tag:Origin-%s' % tag_key, 'Values': [tag_value]}
        ])
    except BotoCoreError as exc:
        logging.error("Getting all previously created snapshots failed:\n%s", exc)
        sys.exit(1)

    for volume_id in list(set([snapshot['VolumeId'] for snapshot in snapshots['Snapshots']])):
        snapshots_for_volume = [s for s in snapshots['Snapshots'] if s['VolumeId'] == volume_id]
        snapshots_for_volume = sorted(snapshots_for_volume, key=lambda x: x['StartTime'])

        while len(snapshots_for_volume) > num_backups:
            try:
                snapshot = snapshots_for_volume.pop(0)
                client.delete_snapshot(SnapshotId=snapshot['SnapshotId'])
            except BotoCoreError as exc:
                logging.error("Deleting snapshot %s (%s) belonging to volume %s failed:\n%s",
                              snapshot['SnapshotId'],
                              snapshot['StartTime'],
                              snapshot['VolumeId'],
                              exc)
            else:
                logging.info("Sucessfully deleted snapshot %s (%s) belonging to volume %s",
                             snapshot['SnapshotId'],
                             snapshot['StartTime'],
                             snapshot['VolumeId'])


def main():
    """Main method for setup.

    Setup command line parsing, the AWS connection and call the functions
    containing the actual logic.
    """
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.INFO)
    logging.getLogger('botocore').setLevel(logging.CRITICAL)

    parser = argparse.ArgumentParser(description='Script to automate \
                                     snapshotting of EBS volumes')
    parser.add_argument('--aws-access-key-id',
                        dest='aws_access_key_id',
                        help='Specify a value here if you want to use a '
                        'different AWS_ACCESS_KEY_ID than configured in the '
                        'AWS CLI.')
    parser.add_argument('--aws-secret-access-key',
                        dest='aws_secret_access_key',
                        help='Specify a value here if you want to use a '
                        'different AWS_SECRET_ACCESS_KEY than configured in '
                        'the AWS CLI.')
    parser.add_argument('--profile',
                        dest='profile_name',
                        help='The AWS CLI profile to use. Defaults to the '
                        'default profile.')
    parser.add_argument('--region',
                        dest='region_name', default='us-east-1',
                        help='The AWS region to connect to. Defaults to the '
                        'one configured for the AWS CLI.')
    parser.add_argument('-n', '--num-backups', dest='num_backups', type=int,
                        default=14,
                        help='The number of backups for each volume to keep')
    parser.add_argument('-t', '--tag', dest='tag', default='Lifecycle:legacy',
                        help='Key and value (separated by a colon) of a tag '
                        'attached to instances whose EBS volumes should be '
                        'backed up')
    args = parser.parse_args()

    session_args = {key: value for key, value in list(vars(args).items())
                    if key in ['aws_access_key_id',
                               'aws_secret_access_key',
                               'profile_name',
                               'region_name']}
    try:
        session = Session(**session_args)
        client = session.client('ec2')
    except BotoCoreError as exc:
        logging.error("Connecting to the EC2 API failed: %s", exc)
        sys.exit(1)

    tag_key_value = args.tag.split(':')
    if len(tag_key_value) != 2:
        logging.error("Given tag key value: \"%s\" is invalid.", args.tag)
        sys.exit(1)
    tag_key = tag_key_value[0]
    tag_value = tag_key_value[1]

    make_snapshots(client, tag_key, tag_value)
    delete_old_snapshots(client, tag_key, tag_value, args.num_backups)


if __name__ == "__main__":
    main()
