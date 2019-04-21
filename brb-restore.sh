#!/bin/bash
#
# brb-restore.sh
#

#
# If anything fails, abort.
#
set -e

#
# Variables
#
opticalDrive=$1
restoreDir=$2
backupDriveName=backupImage
backupDriveContainerName=$backupDriveName'Encrypted'
bar="======================================="

#
# Get password
#
echo
echo "LUKS Password for discs: "
read -s password
echo

#
# Will need to ask the user each time whether they have another disc
#
function ask_ready {
    read -p "Have another CD to restore from in $opticalDrive (y/n): " -n 1 -r
    }
ask_ready

until [[ ! $REPLY =~ ^[Yy]$ ]]; do
    #
    # Mount the disc
    #
    echo
    echo "Mounting disc..."
    echo $bar
    echo -n $password | sudo cryptsetup luksOpen $opticalDrive $backupDriveContainerName -d -
    sudo mkdir -p /mnt/backups/restore
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

    else
        echo
        echo "Skipping..."
        echo $bar

    fi

    #
    # Clean up
    #
    echo
    echo "Unmounting everything & cleaning up..."
    echo $bar
    sudo umount /mnt/backups/$backupDriveName
    sudo cryptsetup luksClose $backupDriveContainerName

    #
    # Another?
    #
    ask_ready

done

echo "Done!"
echo
