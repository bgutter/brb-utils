#!/bin/bash

#
# bd-restore.sh
#
# Restore ISOs from bd-backup.sh
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
loopDevice=$(losetup -f)
isoFile=$1
restoreDir=$2
backupDriveName=backupImage
backupDriveContainerName=$backupDriveName'Encrypted'
bar="======================================="

#
# Mount the ISO to a loop device, mount
# the LUKS logical volume, then mount the
# EXT4 partition.
#
echo
echo "Mounting $isoFile..."
echo $bar
sudo losetup $loopDevice $isoFile
sudo cryptsetup luksOpen $loopDevice $backupDriveContainerName
sudo mount /dev/mapper/$backupDriveContainerName /mnt/backups/$backupDriveName

#
# Echo the contents of the manifest and the map,
# ask for permission to continue
#
echo
echo "Found the following files:"
echo $bar
cat /mnt/backups/$backupDriveName/MANIFEST.TXT
echo
echo "The overall files -> disc map looks like this:"
echo $bar
cat /mnt/backups/$backupDriveName/MAP.TXT
echo
read -p "Continue? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then

    #
    # Rsync the files from the mount back to the restore dir
    #
    echo
    echo "rsync-ing /mnt/backups/$backupDriveName/* (except map and manifest) to $restoreDir..."
    echo $bar
    sudo rsync -a --stats --exclude "lost+found" --exclude "MAP.TXT" --exclude "MANIFEST.TXT" "/mnt/backups/$backupDriveName/" "$restoreDir"
    
    #
    # Verify that all folders in ISO now appear in restore dir
    #
    # TODO
    
fi

#
# Clean up
#
echo
echo "Unmounting everything & cleaning up..."
echo $bar
sudo umount /mnt/backups/$backupDriveName
sudo cryptsetup luksClose $backupDriveContainerName
sudo losetup -d $loopDevice

echo "Done!"
echo
