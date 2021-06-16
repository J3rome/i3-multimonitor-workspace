# i3-MultiMonitor-Workspace

:warning: This software ​i​s a Minimum Viable Product. Been using it for a while on my own setup. There might be some problems, feel free to fill up an issue  :warning:

## The problem

When using `i3 windows manager`, each monitor get assigned an individual workspace. I find it easier to separate tasks/concerns with a virtual workspace spanning across all monitors. I googled for a while but couldn't find a satisfying solution.



## Solution

`i3-multimonitor-workspace` is a python daemon that listen to workspace changes and reflect the changes across all monitors using `i3ipc` commands.



## How does it work

Let's say we have a 3 monitor setup (`HDMI-1`, `DVI-1`, `DP-1`) with 3 global workspaces. The following workspaces will be spawned by the daemon :

```
DVI-1
	1:1
	2:2
	3:3
HDMI-1
	11:1
	12:2
	13:3
DP-1
	21:1
	22:2
	23:3
```

For example, when the user navigate to the workspace `2` using `modKey+2`, the daemon will bring up the workspaces `2`,`12` and `22` thus creating the effect of a `Multi Monitor Workspace`. Specifying the `strip_workspace_numbers` option in the i3 config will ensure that `2` is shown on each monitors instead of `2`, `12` and `22`. Since the daemon is listening to `WORKSPACE_FOCUS` events, there is no need to change keybindings (except for specific cases, see [i3 Configuration](#required-i3-configuration)).



The biggest challenge is to keep all the individual workspaces opened even when there is no spawned window inside it. `i3` is built to clear the workspace when it's empty and the focus to the workspace is lost. To workaround this, we spawn dummy windows that are used as placeholders (This first version uses terminal windows as placeholders which is definitely not the most efficient solution, see [Known Issues](#known-issues) for more details).



## Setup

The following python package is required :

```bash
pip install i3ipc
```

We also make use of these linux packages :

```
xdotool
dmenu
wmctrl
```

Simply cloning this repository and running `python3 i3-multimonitor-workspace.py` will start the daemon. We recommend launching it inside your `i3 config`



### Required i3 configuration

In the future, I hope to find a way to reduce the amount of configuration needed for the daemon to work. In the meantime, here is what you need to add to your configuration :



First, the daemon should be started when `i3` is launched :

```bash
exec_always --no-startup-id "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py"
```

Then, the placeholder windows should be moved to `scratchpad` automatically :

```
for_window [instance="empty_workspace"] move to scratchpad
```

We use an ugly hack to ensure that the placeholders are transparent... We won't need this when we stop using terminal windows as placeholders. This step is optional but without it, you might see some flashes when changing workspace). Add the following lines to your `.bashrc` :

```bash
if [[ ! -z ${DISPLAY} ]]; then
    EMPTY_PLACEHOLDER_WINDOW_ID=$(wmctrl -lpx | grep "$PPID.*empty_workspace" | awk '{print $1}')
    if [[ ! -z ${EMPTY_PLACEHOLDER_WINDOW_ID} ]];then
        transset --id ${EMPTY_PLACEHOLDER_WINDOW_ID} 0
    fi
fi
```



Finally, the workspaces must be assigned to each monitors :

```
workspace 0 output DVI-1
workspace 10 output HDMI-1
workspace 20 output DP-1

workspace 1 output DVI-1
workspace 11 output HDMI-1
workspace 21 output DP-1

workspace 2 output DVI-1
workspace 12 output HDMI-1
workspace 22 output DP-1

...

workspace 8 output DVI-1
workspace 18 output HDMI-1
workspace 28 output DP-1

workspace 9 output DVI-1
workspace 19 output HDMI-1
workspace 29 output DP-1
```



### Optional i3 configuration

To enable workspace renaming (this keybinding will rename the current `multimonitor workspace`):

```bash
bindsym $superKey+$altKey+r exec "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --rename"
```



To enable back-and-forth between 2 `multimonitor workspace` (Similar to `Alt+Tab`) :

```bash
bindsym $altKey+Tab exec "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --back_and_forth"
```



When moving a window to a specific workspace with the default keybindings (`modKey+Shift+3`), the window will always be placed in the center monitor. The `--move_to_workspace` parameter can be used to move the window to another workspace and keeping the window in the same monitor. Use this configuration to enable this :

```bash
bindsym $altKey+Shift+0 exec --no-startup-id "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --move_to_workspace 0"
bindsym $altKey+Shift+1 exec --no-startup-id "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --move_to_workspace 1"
bindsym $altKey+Shift+2 exec --no-startup-id "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --move_to_workspace 2"
bindsym $altKey+Shift+3 exec --no-startup-id "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --move_to_workspace 3"
bindsym $altKey+Shift+4 exec --no-startup-id "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --move_to_workspace 4"
bindsym $altKey+Shift+5 exec --no-startup-id "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --move_to_workspace 5"
bindsym $altKey+Shift+6 exec --no-startup-id "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --move_to_workspace 6"
bindsym $altKey+Shift+7 exec --no-startup-id "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --move_to_workspace 7"
bindsym $altKey+Shift+8 exec --no-startup-id "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --move_to_workspace 8"
bindsym $altKey+Shift+9 exec --no-startup-id "python3 /opt/i3-multimonitor-workspace/i3-multimonitor-workspace.py --move_to_workspace 9"
```





## Tradeoff

At first, I wanted this software to be as transparent as possible which is why I am listening to `WORKSPACE_FOCUS` events. This however doesn't give the best user experience. The workspace identifiers might flash when changing the `multimonitor workspace` because the individual workspace get removed and recreated quickly. This is a limitation of being event based (When we receive the `WORKSPACE_FOCUS` event, the previous workspace has already lost it's focus so it already got removed by `i3`). One way to workaround this would be to do all workspace changes via keybindings (replacing all the default one with specific one). I might explore this later.



## Limitations/Known issues

* Doesn't support plugging/unplugging of monitors. The daemon must be restarted and the config must be modified according to the new monitor setup (the workspace monitor assignement config)
* The number of multimonitor workspaces is limited to `10` (`10 * NbMonitor` individual workspaces). 
* The daemon will only start when more than 1 monitor is connected (loosing the `--back_and_forth` and `--rename` capabilities)
* The daemon keep the workspace names and the last focused workspace in memory, should write to file.
* `--back_and_forth` can be a bit slow
* When fast switching between `multimonitor workspace`, an individual workspace might get "deleted". Focusing back on this `multimonitor workspace` should sync back the individual workspaces.
* When moving a container to a new workspace (Alt+Shift+7 when workspace 7 doesn't exist), Only the workspace on the main monitor will be created. Not a big issue, when focusing the newly created workspace the other workspaces will be created.
* Sometime when a window is in fullscreen and we switch workspace, the container is not fullscreen anymore when we get back to the workspace.



## TODO :

* Publish a package on `pip`
* More testing with different monitor configurations
* Script that auto generate the necessary `i3 config`
* Add possibility to specify default workspaces (Will be automatically created/renamed on launch)
* Fix issues in [Limitations/Known Issues](#limitations/known-issues)

## Known Issues
* When changing global workspace from an empty workspace, the workspace identifier disappear for short time which cause jittering in the status bar.
	* Not sure how to fix this since we don't have a `WORKSPACE_PRE_EMPTY` event, when the `WORKSPACE_EMPTY` event is triggered, the empty workspace has already been killed.
* When changing workspaces too quickly, the multi-monitor workspace won't be handled (Pressing down a binding for "Next workspace" and not releasing it for a couple of seconds)
	* When the user stop changing workspaces, they will most probably be out of sync. Simply changing to another workspace and coming back will resync the workspaces


## Version infos
```
Tested on Ubuntu 18.04 with Python 3.6.9 and a 3 monitor setup
i3 version 4.16.1-175-gac795ae3 (2019-05-03, branch "gaps-next") 
© 2009 Michael Stapelberg and contributors
```

I know this is an old version of i3, will test with a newer version when I have some time.



## Contributing

Pull requests are welcome !