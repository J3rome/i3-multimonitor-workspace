# i3-MultiMonitor-Workspace

## TODO:
* Add explanation of what this is
* Explain how workspaces are chosen for each monitor (1,11,21...)
* Add mention that this limit the number of workspace to 10 global workspaces (10 * nb_monitor individual workspaces)
* Add setup instructions
* Add mention that this won't run if you only have 1 monitor (Will not stop if monitors are disconnected tho)
* Add mention that no special keybindings are required,
	* Required linux packages
	* .bashrc modifications
	* i3 config modifications
* Add mention of how to create a keybinding for toggling usage of this tool
* Do some tests with 2 and 4+ monitors
* Create script that generate i3 config lines
* Test with named workspaces

## Known Issues
* When changing global workspace from an empty workspace, the workspace identifier disappear for short time which cause jittering in the status bar.
	* Not sure how to fix this since we don't have a `WORKSPACE_PRE_EMPTY` event, when the `WORKSPACE_EMPTY` event is triggered, the empty workspace has already been killed.
* When changing workspaces too quickly, the multi-monitor workspace won't be handled (Pressing down a binding for "Next workspace" and not releasing it for a couple of seconds)
	* When the user stop changing workspaces, they will most probably be out of sync. Simply changing to another workspace and coming back will resync the workspaces


## More infos
```
Tested on Ubuntu 18.04 with Python 3.6.9 and a 3 monitor setup
i3 version 4.16.1-175-gac795ae3 (2019-05-03, branch "gaps-next") 
© 2009 Michael Stapelberg and contributors
```