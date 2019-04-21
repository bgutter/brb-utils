#!/bin/bash

#
# brb-make-isos.sh
#
# Divide some directory sanely into multiple volumes write
# each one to a LUKS encrypted EXT4 filesystem on a BD-R
# sized ISO.
#

#
# If anything fails, quit.
#
set -e
