#!/bin/bash

#
# If anything fails, quit.
#
set -e

#
# Options
#
backupPath="$1"
maxDivSize="$2"
maxDiskSize="$3"
isoDir="$4"
divdirPath=./divdir.py

#
# Book-keeping variables
#
loopDevice=$(losetup -f)
wkspDir=$(mktemp -d)
backupDriveName=backupImage
backupDriveContainerName=$backupDriveName'Encrypted'
bar="======================================="

#
# Reassure myself that this script does what
# I think it does (won't remember writing it
# a year from now).
#
echo
echo "Backing up contents of:                    $backupPath"
echo "Leaving ISOs in:                           $isoDir"
echo "Max division size is:                      $maxDivSize"
echo "Max disk size is:                          $maxDiskSize"
echo

#
# Generate manifests
#
echo
echo "Finding a reasonable way to divide directories in $backupPath..."
echo $bar
sudo python $divdirPath $backupPath $maxDivSize $wkspDir

#
# Show the generated file mapping and check that it's okay
#
echo "I came up with the following file -> disc map..."
echo $bar
cat $wkspDir/map.txt
echo
read -p "Is this okay? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo
    echo "Then do it yourself."
    echo
    exit
fi

#
# Get password
#
echo
echo "LUKS Password for created discs: "
read -s password
echo
echo "Confirm: "
read -s pwconfirm
echo
if [ "$password" != "$pwconfirm" ]; then
    echo "Passwords do not match!"
    echo
    exit
fi

#
# For each manifest
#
for manifestFile in $wkspDir/manifest-*.txt; do

    #
    # Get the extensionless basename of manifestFile
    #
    manifestFileId=${manifestFile##*/}
    manifestFileId=${manifestFileId%.*}

    #
    # Create the ISO
    #
    isoFile=$isoDir/$manifestFileId.iso
    echo
    echo "Creating $isoFile and mounting it to $loopDevice"
    echo $bar
    fallocate -l $maxDiskSize $isoFile
    sudo losetup $loopDevice $isoFile

    #
    # Create LUKS volume on the loop device, and
    # then create an EXT4 volume on the payload.
    #
    echo
    echo "Creating LUKS volume, mounting it, and formatting to EXT4..."
    echo $bar
    echo -n $password | sudo cryptsetup -y luksFormat $loopDevice -d -
    echo -n $password | sudo cryptsetup luksOpen $loopDevice $backupDriveContainerName -d -
    sudo mkfs.ext4 -b 2048 /dev/mapper/$backupDriveContainerName

    #
    # Mount ISO
    #
    sudo mkdir -p /mnt/backups/$backupDriveName
    sudo mount /dev/mapper/$backupDriveContainerName /mnt/backups/$backupDriveName

    #
    # rsync each entry in the manifest
    #
    echo
    echo "rsync-ing each line in $manifestFileId to /mnt/backups/$backupDriveName"
    echo $bar
    while read in
    do
        echo
        echo "--> $in"
        sudo rsync -Ra --stats "$in" /mnt/backups/$backupDriveName/
    done < $manifestFile

    #
    # Copy in the manifest & map files
    #
    echo
    echo "Copying manifest and map files..."
    echo $bar
    sudo cp $manifestFile /mnt/backups/$backupDriveName/MANIFEST.TXT
    sudo cp $wkspDir/map.txt /mnt/backups/$backupDriveName/MAP.TXT

    #
    # Unmount volume and encrypted container
    #
    echo
    echo "Unmounting filesystem, closing LUKS volume, and deleting loop device..."
    echo $bar
    sudo umount /mnt/backups/$backupDriveName
    sudo cryptsetup luksClose $backupDriveContainerName
    sudo losetup -d $loopDevice

done

echo
echo "Deleting temp directory"
echo $bar
rm -rf $wkspDir

echo "Done!"
echo
