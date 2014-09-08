#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Author: Daniel Roschka <daniel@smaato.com>
Copyright: Smaato Inc. 2014
URL: https://github.com/smaato/ebs-snapshot-automation

A small script meant to be run as a cronjob to regularly snapshot EBS volumes attached to EC2
instances and handle rolling backups for these snapshots.

Instances to backup are selected by a configured tag, so the instances to backup can be easily
selected by adding or removing the appropriate tag to the EC2 instance, without any configuration
change needed for this script.
'''

import argparse
from boto.ec2 import connect_to_region
from boto.exception import BotoServerError
from datetime import datetime
from itertools import chain
import logging
import sys


def make_snapshots(connection, tag):
    '''
    Creates a snapshot for every EBS volume attached to an instance which contains the tag used
    to filter for instances to backup.
    '''
    tag_key_value = tag.split(':')
    if len(tag_key_value) != 2:
        logging.error("Given tag key value: \"%s\" is invalid.", tag)
        sys.exit(1)

    tag_filter = {'tag:%s' % tag_key_value[0] : '%s' % tag_key_value[1]}
    reservations = connection.get_all_reservations(filters=tag_filter)
    instances = list(chain.from_iterable([x.instances for x in reservations]))
    if not instances:
        logging.warning("Couldn't find any instances whose volumes need snapshotting. Aborting …")
        sys.exit(0)

    # filter the volumes for the ones attached to the tagged instances
    volumes = [v for v in connection.get_all_volumes() if v.status == 'in-use' and
	                    v.attach_data.instance_id in [i.id for i in instances]]
    if not volumes:
        logging.warning("Found instances to backup, but no attached volumes. Something is fishy \
                         here. Aborting …")
        sys.exit(1)

    for instance in instances:
        volumes_tmp = [v for v in volumes if v.attach_data.instance_id == instance.id]
        for volume in volumes_tmp:
            try:
                if 'Name' in instance.tags:
                    snapshot = volume.create_snapshot(description='automated snapshot of volume \
                                                      %s attached as %s to %s (%s)' %
                                                      (volume.id,
                                                       volume.attach_data.device,
                                                       instance.tags['Name'],
                                                       volume.attach_data.instance_id))
                else:
                    snapshot = volume.create_snapshot(description='automated snapshot of volume \
                                                      %s attached as %s to %s' %
                                                      (volume.id,
                                                       volume.attach_data.device,
                                                       volume.attach_data.instance_id))
            except BotoServerError as exc:
                logging.error("Creating a snapshot of volume %s failed:\n%s", volume.id, exc)
            else:
                logging.info("Creating snapshot %s of volume %s", snapshot.id, volume.id)
            try:
                if 'Name' in instance.tags:
                    snapshot.add_tag('Name', '%s %s %s' % (instance.tags['Name'],
                                     volume.attach_data.device,
                                     datetime.now().strftime('%Y-%m-%d %H:%M')))
                else:
                    snapshot.add_tag('Name', '%s %s %s' % (volume.attach_data.instance_id,
                                     volume.attach_data.device,
                                     datetime.now().strftime('%Y-%m-%d %H:%M')))
                snapshot.add_tag('Creator', 'ebs_snapshot_automation')
                snapshot.add_tag('Origin-Instance', volume.attach_data.instance_id)
            except BotoServerError as exc:
                logging.error("Tagging the snapshot %s of volume %s failed:\n%s",
                               snapshot.id,
                               volume.id,
                               exc)


def delete_old_snapshots(connection, num_backups):
    '''
    Removes the oldest snapshots for a volume if there are more snapshots than configured in
    num_backups
    '''
    try:
        snapshots = connection.get_all_snapshots(filters={'tag:Creator' : 'ebs_snapshot_automation'})
    except BotoServerError as exc:
         logging.error("Getting all previously created snapshots failed:\n%s", exc)
         sys.exit(1)

    for volume_id in list(set([snapshot.volume_id for snapshot in snapshots])):
        snapshots_for_volume = [s for s in snapshots if s.volume_id == volume_id]
        snapshots_for_volume = sorted(snapshots_for_volume, key=lambda x: x.start_time)

        while len(snapshots_for_volume) > num_backups:
            try:
                snapshot = snapshots_for_volume.pop(0)
                snapshot.delete()
            except BotoServerError as exc:
                logging.error("Deleting snapshot %s (%s) belonging to volume %s failed:\n%s",
                             snapshot.id,
                             snapshot.start_time,
                             snapshot.volume_id,
                             exc)
            else:
                logging.info("Deleting snapshot %s (%s) belonging to volume %s",
                             snapshot.id,
                             snapshot.start_time,
                             snapshot.volume_id)


def main():
    '''
    Setup the commandline parsing, the AWS connection and call the functions containing the actual
    logic.
    '''
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)

    parser = argparse.ArgumentParser(description='Script to automate \
                                     snapshotting of EBS volumes')
    parser.add_argument('-a', '--access-key', dest='aws_access_key',
                        required=True, help='The AWS access key to use')
    parser.add_argument('-s', '--secret-key', dest='aws_secret_key',
                        required=True, help='The AWS secret key to use')
    parser.add_argument('-r', '--region', dest='region', default='us-east-1',
                        help='The AWS region to connect to')
    parser.add_argument('-n', '--num-backups', dest='num_backups', type=int, default=14,
                        help='The number of backups for each volume to keep')
    parser.add_argument('-t', '--tag', dest='tag', default='Lifecycle:legacy',
                        help='Key and value (separated by a colon) of a tag attached to instances \
                              whose EBS volumes should be backed up')
    args = parser.parse_args()

    try:
        connection = connect_to_region(args.region,
                                       aws_access_key_id=args.aws_access_key,
                                       aws_secret_access_key=args.aws_secret_key)
    except BotoServerError as exc:
        logging.error("Establishing a connection to AWS failed:\n%s", exc)

    make_snapshots(connection, args.tag)
    delete_old_snapshots(connection, args.num_backups)


if __name__ == "__main__":
    main()
