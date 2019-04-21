#!/bin/bash

#
# bd-restore.sh
#
# Restore volumes from bd-backup.sh
#
# Read documentation there.
#

#
# If anything fails, quit
#
set -e

#
# Options
#
restoreDir=/encrypted_data_disk/temp/restored
date=2019-04-19
manifestFileId=0

#
# Book-keeping variables
#
loopDevice=$(losetup -f)
isoFile=/encrypted_data_disk/temp/$date-manifest-$manifestFileId.iso

#
# Mount the ISO to a loop device, mount
# the LUKS logical volume, then mount the
# EXT4 partition.
#
sudo losetup $loopDevice $isoFile
sudo cryptsetup luksOpen $loopDevice $backupDriveContainerName
sudo mount /dev/mapper/$backupDriveContainerName /mnt/backups/$backupDriveName

#
# Rsync the files from ISO back to 
#
