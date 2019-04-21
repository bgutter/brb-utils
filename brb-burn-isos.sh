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
# Burn each ISO
#
for isoFile in $isoList; do

    echo
    echo "Burning $isoFile..."
    echo $bar
    read -p "Press enter when a blank disc is ready. Type 's' to skip:" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]
    then
       growisofs -use-the-force-luke=spare=none -dvd-compat -Z $burnerDevice=$isoFile
    fi

done

echo "Done!"
