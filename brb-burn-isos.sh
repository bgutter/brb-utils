#!/bin/bash

#
# If anything fails, quit.
#
set -e

#
# Get the input arguments
#
burnerDevice=${@:$#}
isoList=${*%${!#}}
bar="======================================="

#
# For each passed ISO
#
for isoFile in $isoList; do

    #
    # Burn the ISO
    #
    echo
    echo "Burning $isoFile..."
    echo $bar
    read -p "Press enter when a blank disc is ready. Type 's' to skip:" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]
    then
       growisofs -use-the-force-luke=spare=none -dvd-compat -Z $burnerDevice=$isoFile
    fi

    #
    # Read the file back from disk and compare checksum
    # against the ISO image
    #
    # TODO

done

echo "Done!"
