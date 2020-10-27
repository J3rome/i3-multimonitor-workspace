#####################################################
##           i3 Multi monitor workspace            ##
#####################################################
##  Author : J3romee (https://github.com/j3romee)  ##
##  Date : October 2020                            ##
##  License : GNU General Public License v3        ##
#####################################################

# TODO : More stuff need to be added to i3 config, simply refer to README ?

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
import argparse
import threading

from i3ipc import Connection, Event

from actions import rename_current_workspace, rewrite_workspace_names
from misc import get_mouse_position, set_mouse_position, setup_exit_signal_handling, clear_all_placeholders

# TODO : Define a way to have named workspace at start (from config) but still keep the workspace 
# TODO : Do some argument parsing to provide actions via this script
#           - Move a container to a specific global workspace. Making sure that the moved container stay on the same monitor
#           - Move all containers of a global workspace to another
#           - Move container to next workspace & focus (See current script)

# TODO : Moving a window to a monitor (Mod+Shift+Nb) should send the window to the same monitor

# FIXME : Still some wiggling (workspaces in status bar) when moving from an empty window
#         - Not sure how we could solve this, we would need a hook WORKSPACE_PRE_EMPTY. 
#           When we enter the WORKSPACE_EMPTY event, the workspace has already been killed so spawning a new placeholder create the wiggling

# TODO : Don't use actual terminal windows as placeholders
#        - Force geometry on windows so that they are at the top right of the monitor and take minimal space (Right now we could have a transparent placeholder floating over the monitor)
#        - IF we change this, we need to handle transparency a different way then via .bashrc
#        - Spawning windows from python would make it so that if the program crash, all placeholders will automatically be killed
#           We could also set the transparency when creating the windows, no need for the .bashrc magic         

# TODO : Cleanup MY config file, remove some binding that are rendered useless by this


parser = argparse.ArgumentParser('i3 Multi Monitor workspace manager')

parser.add_argument("--rename", help="Will rename all workspaces in global workspace (From dmenu input)", 
                    action="store_true")

parser.add_argument("--dont_rewrite_workspace_number", help="Will use the individual workspace id instead of the global id", 
                    action="store_true")


# Placeholder windows handling
def create_placeholder_windows(i3_inst, workspace_ids):
    create_placeholder_cmd = ""
    for workspace_id in workspace_ids:
        class_name = f"empty_workspace_{workspace_id}"
        create_placeholder_cmd += f"exec --no-startup-id i3-sensible-terminal --name '{class_name}'; "
        i3_inst.spawned_placeholders.append(class_name)

    i3_inst.command(create_placeholder_cmd)


def show_placeholder_windows(i3_inst, workspace_ids):
    show_placeholders_cmd = ""
    for workspace_id in workspace_ids:
        show_placeholders_cmd += f'[instance="empty_workspace_{workspace_id}$"] move to workspace number {workspace_id}; '

    i3_inst.command(show_placeholders_cmd)


def focus_workspaces(i3_inst, workspace_ids, focused_workspace, focus_last):
    # No need to refocus the workspace that triggered the WORKSPACE_FOCUS event, we just need to hide the placeholder
    focus_workspace_cmd = f'[instance="empty_workspace_{focused_workspace}$"] move to scratchpad; '
    for workspace_id in workspace_ids:
        if workspace_id != focus_last and workspace_id != focused_workspace:
            focus_workspace_cmd += f'workspace number {workspace_id}; [instance="empty_workspace_{workspace_id}$"] move to scratchpad; '

    # Focus last the workspace on the same monitor
    focus_workspace_cmd += f'workspace number {focus_last}; [instance="empty_workspace_{focus_last}$"] move to scratchpad; '

    i3_inst.command(focus_workspace_cmd)


# Workspace handling (killing/focusing)
def kill_global_workspace(i3_inst, workspace_ids):
    kill_placeholders_cmd = ""
    for workspace_id in workspace_ids:
        class_name = f'empty_workspace_{workspace_id}'
        kill_placeholders_cmd += f'[instance="{class_name}$"] kill;'
        i3_inst.spawned_placeholders.remove(class_name)

    i3_inst.command(kill_placeholders_cmd)


# Focus event handler
def on_workspace_focus(i3_inst, event):
    from_workspace = event.old.name
    from_workspace_id = from_workspace.split(':')[0]
    to_workspace = event.current.name
    to_workspace_id = to_workspace.split(":")[0]
    changing_global_workspace = i3_inst.current_workspace_id != to_workspace_id[-1]


    if 'i3_scratch' in from_workspace:
        # Ignore focus from scratchpad
        return

    if changing_global_workspace:
        # FIXME : maybe we should use a try, finally for the lock?
        if not i3_inst.focus_lock.acquire(blocking=False):
            return

        # Save mouse position (Prevent jitter when spawning/focusing other workspaces)
        initial_mouse_position = get_mouse_position()
        
        # Retrieve global workspace id
        new_global_workspace_id = to_workspace_id[-1]
        old_global_workspace_id = from_workspace_id[-1]
        i3_inst.current_workspace_id = new_global_workspace_id

        # Define which monitor should be focused (We want to keep focus on the same monitor)
        same_monitor_target_workspace = f"{from_workspace[0]}{new_global_workspace_id}" if len(from_workspace_id) == 2 else f"{new_global_workspace_id}"

        # Individual workspace ids
        new_workspace_child_ids = [f"{i}{new_global_workspace_id}" if i > 0 else f"{new_global_workspace_id}" for i in range(i3_inst.nb_monitor)]
        old_workspace_child_ids = [f"{i}{old_global_workspace_id}" if i > 0 else f"{old_global_workspace_id}" for i in range(i3_inst.nb_monitor)]

        # Check if the old global workspace is empty
        existing_workspaces = i3_inst.get_tree().workspaces()
        new_workspace_existing_childs = [w.name for w in existing_workspaces if w.name.split(":")[0][-1] == new_global_workspace_id]
        old_global_workspaces = [w for w in existing_workspaces if w.name.split(":")[0] in old_workspace_child_ids]
        old_empty_workspaces = [w for w in old_global_workspaces if len(w.descendants()) == 0]

        # If all old workspaces are empty, kill placeholders
        if len(old_global_workspaces) == len(old_empty_workspaces):
            kill_global_workspace(i3_inst, old_workspace_child_ids)
        
        # If the placeholder windows exists in the old workspace, show them
        elif f'empty_workspace_{old_workspace_child_ids[0]}' in i3_inst.spawned_placeholders:
            show_placeholder_windows(i3_inst, old_workspace_child_ids)

            # FIXME : When this condition is true, the number in the workspace bar disappear and reappear...
            if i3_inst.rewrite_workspace_names and from_workspace.count(":") > 0 and len(event.old.descendants()) == 0:
                # The previous workspace got deleted, we need to rename it again
                i3_inst.command(f'rename workspace {from_workspace_id} to "{from_workspace}"')

        # If placeholders windows for the new workspace are not spawned, create them
        if f'empty_workspace_{new_workspace_child_ids[0]}' not in i3_inst.spawned_placeholders:
            create_placeholder_windows(i3_inst, new_workspace_child_ids)


        # Focus all workspaces belonging to the new global workspace
        focus_workspaces(i3_inst, new_workspace_child_ids, focused_workspace=to_workspace_id, 
                         focus_last=same_monitor_target_workspace)

        if i3_inst.rewrite_workspace_names and len(new_workspace_existing_childs) < i3_inst.nb_monitor:
            # Workspaces are being created, rewrite the workspaces names so they show the have the same name
            rewrite_workspace_names(i3_inst, new_workspace_child_ids)

        # Reset mouse position
        set_mouse_position(initial_mouse_position[0], initial_mouse_position[1])

        # Unlock workspace change in 50 ms 
        # This prevent event overloading when changing workspaces super fast
        threading.Timer(0.01, i3_inst.focus_lock.release).start()


if __name__ == "__main__":
    args = parser.parse_args()
    i3 = Connection()

    # Retrieve the number of monitors
    i3.nb_monitor = len([o for o in i3.get_outputs() if o.active])

    if i3.nb_monitor <= 1:
        print("Need at least 2 monitors to use global workspaces. Terminating.")
        exit(0)

    # Set initial workspace
    i3.current_workspace_name = i3.get_tree().find_focused().workspace().name
    i3.current_workspace_id = i3.current_workspace_name.split(":")[0][-1]

    # Keep track of spawned placeholders
    i3.spawned_placeholders = []

    # Lock to prevent multiple e
    i3.focus_lock = threading.Lock()

    # FIXME : Are both these options really needed/wired ?
    # TODO : Set those to False if the config doesn't permit strip_workspace_numbers
    i3.rewrite_workspace_names = not args.dont_rewrite_workspace_number

    if args.rename:
        rename_current_workspace(i3)
        exit(0)

    # Multi Monitor workspace daemon
    if i3.rewrite_workspace_names:
        all_workspace_names = [w.name for w in i3.get_tree().workspaces() if 'i3_scratch' not in w.name]
        rewrite_workspace_names(i3, all_workspace_names)

    # We make sure that no empty_workspace placeholders are left over from previous run 
    # (Can only happen if we receive SIGKILL or SIGSTOP, otherwise placeholders would have been killed on exit)
    clear_all_placeholders(i3)

    # Clean exit handling (will kill placeholders on exit)
    setup_exit_signal_handling(i3)

    # Setup i3 event handlers
    i3.on(Event.WORKSPACE_FOCUS, on_workspace_focus)

    # Start event handling loop
    i3.main()

