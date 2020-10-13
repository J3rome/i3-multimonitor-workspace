#####################################################
##           i3 Multi monitor workspace            ##
#####################################################
##  Author : J3romee (https://github.com/j3romee)  ##
##  Date : October 2020                            ##
##  License : GNU General Public License v3        ##
#####################################################

####################################################################################
# To prevent windows showing for a couple of milliseconds when changing workspace,
# Add the following lines to your .bashrc file (Linux package 'wmctrl' required !) :
#
#   EMPTY_PLACEHOLDER_WINDOW_ID=$(wmctrl -lpx | grep "$PPID.*empty_workspace" | awk '{print $1}')
#   if [[ ! -z ${EMPTY_PLACEHOLDER_WINDOW_ID} ]];then
#       transset --id ${EMPTY_PLACEHOLDER_WINDOW_ID} 0
#   fi
#
####################################################################################
#
# The 'xdotool' linux package is also needed to prevent mouse jittering
#
####################################################################################

import subprocess
import signal
from datetime import datetime
from datetime import timedelta

from i3ipc import Connection, Event

# TODO : Small program to auto generate config based on available monitors. (Can we use regex to assign workspaces to a monitor ? this would greatly simplify the config)


# TODO : Add function to enable/disable on the fly

# FIXME : Loop prevention is not really good. Counting the number of changes per 2 seconds is highly dependent on the CPU current usage
#         A really slow computer could get stuck in a loop because it would take longer than THRESHOLD to change workspaces
#         - BEST solution would still be to disable/unbind the workspace changes keys

# FIXME : Still some wiggling (workspaces in status bar) when moving from an empty window
#         - Not sure how we could solve this, we would need a hook WORKSPACE_PRE_EMPTY. 
#           When we enter the WORKSPACE_EMPTY event, the workspace has already been killed so spawning a new placeholder create the wiggling

# TODO : Don't use actual terminal windows as placeholders
#        - Force geometry on windows so that they are at the top right of the monitor and take minimal space (Right now we could have a transparent placeholder floating over the monitor)
#        - IF we change this, we need to handle transparency a different way then via .bashrc
#        - Spawning windows from python would make it so that if the program crash, all placeholders will automatically be killed
#           We could also set the transparency when creating the windows, no need for the .bashrc magic         



# TODO : Do some test with 2 monitors

# TODO : Cleanup MY config file, remove some binding that are rendered useless by this

def getMousePosition():
    raw_out = subprocess.check_output('xdotool getmouselocation'.split(' ')).decode()
    x_y = raw_out.split(' screen')[0].split(' y:')
    x = int(x_y[0].split('x:')[-1])
    y = int(x_y[-1])

    return x, y


def setMousePosition(x, y):
    subprocess.check_output(f'xdotool mousemove {x} {y}'.split(' '))


def create_placeholder_windows(i3_inst, workspace_ids):
    create_placeholder_cmd = ""
    for workspace_name in workspace_ids:
        class_name = f"empty_workspace_{workspace_name}"
        create_placeholder_cmd += f"exec --no-startup-id i3-sensible-terminal --name '{class_name}'; "
        i3.spawned_placeholders.append(class_name)

    i3_inst.command(create_placeholder_cmd)


def clear_all_placeholders(i3_inst):
    i3_inst.command('[instance="empty_workspace"] kill')


def show_placeholder_windows(i3_inst, workspace_ids):
    show_placeholders_cmd = ""
    for workspace_id in workspace_ids:
        show_placeholders_cmd += f'[instance="empty_workspace_{workspace_id}$"] move to workspace {workspace_id}; '

    i3_inst.command(show_placeholders_cmd)


def kill_global_workspace(i3_inst, workspace_ids):
    kill_placeholders_cmd = ""
    for workspace_id in workspace_ids:
        kill_placeholders_cmd += f'[instance="empty_workspace_{workspace_id}$"] kill;'

    i3_inst.command(kill_placeholders_cmd)


def focus_workspaces(i3_inst, workspace_ids, focused_workspace, focus_last):
    # No need to refocus the workspace that triggered the WORKSPACE_FOCUS event, we just need to hide the placeholder
    focus_workspace_cmd = f'[instance="empty_workspace_{focused_workspace}$"] move to scratchpad; '
    for workspace_name in workspace_ids:
        if workspace_name != focus_last and workspace_name != focused_workspace:
            focus_workspace_cmd += f'workspace {workspace_name}; [instance="empty_workspace_{workspace_name}$"] move to scratchpad; '

    # Focus last the workspace on the same monitor
    focus_workspace_cmd += f'workspace {focus_last}; [instance="empty_workspace_{focus_last}$"] move to scratchpad; '

    i3_inst.command(focus_workspace_cmd)


def on_workspace_focus(i3_inst, event):
    from_workspace = event.old.name
    to_workspace = event.current.name
    changing_global_workspace = i3.current_workspace != to_workspace[-1]

    if 'i3_scratch' in from_workspace:
        # Ignore focus from scratchpad
        return

    if changing_global_workspace:
        # Keep track of the time delay between global workspace changes

        now = datetime.now()
        i3_inst.workspace_change_timestamps.append(now)
        i3_inst.workspace_change_timestamps = [t for t in i3_inst.workspace_change_timestamps if now - t < i3_inst.one_sec_timedelta]
        

        # FIXME : The threshold is highly correlated with computer usage... 
        #         If the computer is under heavy load, we can still be stuck in an event loop with an acceptable nb_change_per_second
        if len(i3_inst.workspace_change_timestamps) >= i3_inst.workspace_max_nb_change_per_second:
            # Change happened too fast (Might be stuck in a loop)
            # Hide all empty workspace screen & prevent further actions
            i3_inst.command('[instance="empty_workspace"] move to scratchpad')
            return 

        # Save mouse position (Prevent jitter when spawning/focusing other workspaces)
        initial_mouse_position = getMousePosition()
        
        # Retrieve global workspace id
        new_global_workspace_id = to_workspace[-1]
        old_global_workspace_id = from_workspace[-1]
        i3.current_workspace = new_global_workspace_id

        # Define which monitor should be focused (We want to keep focus on the same monitor)
        same_monitor_target_workspace = f"{from_workspace[0]}{new_global_workspace_id}" if len(from_workspace) == 2 else f"{new_global_workspace_id}"

        # Individual workspace ids
        new_workspace_child_ids = [f"{i}{new_global_workspace_id}" if i > 0 else f"{new_global_workspace_id}" for i in range(i3_inst.nb_monitor)]
        old_workspace_child_ids = [f"{i}{old_global_workspace_id}" if i > 0 else f"{old_global_workspace_id}" for i in range(i3_inst.nb_monitor)]

        # Check if the old global workspace is empty
        existing_workspaces = i3_inst.get_tree().workspaces()
        old_global_workspaces = [w for w in existing_workspaces if w.name in old_workspace_child_ids]
        old_empty_workspaces = [w for w in old_global_workspaces if len(w.descendants()) == 0]

        # If all old workspaces are empty
        if len(old_global_workspaces) == len(old_empty_workspaces):
            kill_global_workspace(i3_inst, old_workspace_child_ids)
        
        # If the placeholder windows exists, show them
        elif f'empty_workspace_{old_workspace_child_ids[0]}' in i3_inst.spawned_placeholders:
            show_placeholder_windows(i3_inst, old_workspace_child_ids)

        # Create placeholder windows (If not already spawned)
        if f'empty_workspace_{new_workspace_child_ids[0]}' not in i3_inst.spawned_placeholders:
            create_placeholder_windows(i3_inst, new_workspace_child_ids)

        # Focus all workspaces belonging to the global workspace
        focus_workspaces(i3_inst, new_workspace_child_ids, focused_workspace=to_workspace, 
                         focus_last=same_monitor_target_workspace)

        # Reset mouse position
        setMousePosition(initial_mouse_position[0], initial_mouse_position[1])


def clean_exit(i3_inst):
    print("Clean exit")
    clear_all_placeholders(i3_inst)
    exit(0)


if __name__ == "__main__":
    i3 = Connection()

    # Retrieve the number of monitors
    i3.nb_monitor = len([o for o in i3.get_outputs() if o.active])

    if i3.nb_monitor <= 1:
        print("Need at least 2 monitors to use global workspaces. Terminating.")
        exit(0)

    # Set initial workspace
    i3.current_workspace = i3.get_tree().find_focused().workspace().name[-1]

    # Keep track of spawned placeholders
    i3.spawned_placeholders = []

    # Stats to prevent global workspace switching when it happen too fast
    i3.workspace_change_timestamps = []
    i3.workspace_max_nb_change_per_second = 10
    i3.one_sec_timedelta = timedelta(seconds=1)

    # We make sure that no empty_workspace placeholders are left over from previous run 
    # (Can only happen if we receive SIGKILL or SIGSTOP, otherwise placeholders will be killed on exit)
    clear_all_placeholders(i3)

    # Clean exit handling (will kill placeholders on exit)
    catchable_sigs = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP, signal.SIGCHLD}
    for sig in catchable_sigs:
        signal.signal(sig, lambda x,y: clean_exit(i3))

    # Setup i3 event handlers
    i3.on(Event.WORKSPACE_FOCUS, on_workspace_focus)

    # Start event handling loop
    i3.main()

