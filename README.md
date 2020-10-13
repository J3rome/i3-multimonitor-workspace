# i3-MultiMonitor-Workspace

## TODO:
* Add explanation of what this is
* Explain how workspaces are chosen for each monitor (1,11,21...)
* Add mention that this limit the number of workspace to 10 global workspaces (10 * nb_monitor individual workspaces)
* Add setup instructions
* Add mention that this won't run if you only have 1 monitor (Will not stop if monitors are disconnected tho)
* Add mention that no special keybindings are required,
** Required linux packages
** .bashrc modifications
** i3 config modifications
* Do some tests with 2 and 4+ monitors

## Known Issues
* When changing global workspace from an empty workspace, the workspace identifier disappear for short time which cause jittering in the status bar.
** Not sure how to fix this since we don't have a `WORKSPACE_PRE_EMPTY` event, when the `WORKSPACE_EMPTY` event is triggered, the empty workspace has already been killed.
* When changing workspaces too quickly, the multi-monitor workspace won't be handled
** Ex : Pressing down a binding for "Next workspace" and not releasing it for a couple of seconds. 
*** This will trigger individual workspaces change super fast which will make this program focus even more workspaces (3 focus for each global workspace change).
*** If we see changes faster than 10 workspaces change per seconds, we stop listening to events until the frequency of change get below the threshold.
**** Multi-Monitor workspace will not catch events for up to a second after being forced over the frequency threshold. If this happen, simply wait a second and change to another workspace which will restore the correct individual workspace for each monitor.


## More infos
Tested on Ubuntu 18.04 with Python 3.6.9 and a 3 monitor setup
