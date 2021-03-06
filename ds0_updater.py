#!/usr/bin/env python
# Script provided by DataStax.

# Updating this script requires a rebake of the ami.
#
# The baked version of this script is launched in order to fetch updated ami
# startup code for subsequent phases. Python has already read the baked
# version from disk by the time updates start, with the result that post-bake
# updates to this file are ignored.

import time
import ds0_utils
import logger
import conf


# Figure out the argument we should use with git reset.
def get_git_reset_arg(commitish):
    if not commitish:
        return ''

    (commit_id, err) = logger.exe('git rev-parse ' + commitish)
    if err:
        return ''

    # If the commit-ish is a valid commit id, use it as-is.
    # Otherwise, prefix with the remote (always origin).
    if commit_id.strip() == commitish:
        return commit_id
    else:
        return 'origin/' + commitish

# Wait for cloud-init to finish, it changes all sorts of fundamental
# things on startup (including apt-repo mirrors, but lots of other stuff too)
# and is known to continue doing work after ssh is up and running, and can
# cause all sorts of operations to fail in unexpected ways if it's not finished
logger.info("Waiting for cloud-init to finish...")
# Sleeping a fixed time of 10 seconds is a terrible hack. It would be much
# better to wait for cloud-init to signal that it's finished, which it does
# through the creation of /var/lib/cloud/instance/boot-finished. Unfortunately,
# in Upstart environments, the upstart job for cloud-init also waits for all
# the rc scripts at runlevel 2 to finish... which this file is one of.
# I'm sure it's possible to resolve this circular dependency if we take on
# maintaining upstart scripts, but I'm not ready for that at this point (though
# would welcome a clean pull-request)
time.sleep(10)


# Update the AMI codebase if it's its first boot
if not conf.get_config("AMI", "CompletedFirstBoot"):
    (repository, commitish) = ds0_utils.repository()
    if repository or commitish:
        logger.info('Repository: %s, Commit-ish: %s' % (repository, commitish))

    # Reset the origin if a repository was specified
    if repository:
        logger.exe('git remote rm origin')
        logger.exe('git remote add origin %s' % repository)

    # update the repo
    logger.exe('git fetch', expectError=True) # git fetch outputs to stderr
    logger.exe('git reset --hard %s' % get_git_reset_arg(commitish))

# Start AMI start code
try:
    import ds1_launcher
    ds1_launcher.run()
except:
    logger.exception('ds0_updater.py')
