#!/usr/bin/env python3
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
from pathlib import Path

from i3ipc import Connection, Event

from actions import rename_current_workspace, move_current_container_to_workspace
from actions import do_workspace_back_and_forth, rename_current_workspace
from ipc import create_placeholder_windows, show_placeholder_windows, focus_workspaces, kill_global_workspace, rewrite_workspace_names
from ipc import show_missing_placeholders, update_spawned_placeholder_windows_list
from misc import get_mouse_position, set_mouse_position, setup_exit_signal_handling, clear_all_placeholders
from misc import get_pid_of_running_daemon, send_back_and_forth_signal_to_daemon, set_back_and_forth_handler
from misc import set_rename_handler, send_rename_signal_to_daemon, read_workspace_names_from_file

# FIXME : When a container is in fullscreen and we switch workspace, the container is not fullscreen anymore when we open it
    # Somehow related to moving empty_workspace_placeholders to scratchpad...
    # See focus_workspace() in ipc.py
    # focus_workspace_cmd += f'workspace {workspace_selector}; [instance="empty_workspace_{workspace_id}$"] move to scratchpad; '
    # Commenting the move to scratchpad seems to fix.

    # ONLY HAPPEN WHEN THE CURRENT FOCUSED CHILD WORKSPACE IS IN FULLSCREEN
        # doesn't happen if child 1 is fullscreen and we switch from child 2
        # Not sending the placeholders to 

# FIXME : Get rid of the delay in show_missing_placeholders()

# TODO : setup.py & Making this accessible from anywhere ? Or maybe via python3 -m i3-multi-monitor ?

# TODO : Cleanup MY config file, remove some binding that are rendered useless by this

# TODO : Add option to use other launcher (rofi, provide user cmd)

# TODO : More standalone actions
#           - Move all containers of a global workspace to another
#           - Move container to next workspace & focus (See current script)
# TODO : Don't use actual terminal windows as placeholders
#        - Force geometry on windows so that they are at the top right of the monitor and take minimal space (Right now we could have a transparent placeholder floating over the monitor)
#        - IF we change this, we need to handle transparency a different way then via .bashrc
#        - Spawning windows from python would make it so that if the program crash, all placeholders will automatically be killed
#           We could also set the transparency when creating the windows, no need for the .bashrc magic
# TODO : [ACTUALLY SHOULD REQUIRE THIS OPTION FOR THE SCRIPT TO WORK] Check if strip_workspace_numbers yes is present in config
#       Get config file path : i3 --more-version | grep -oP "Loaded i3 config: \K([\S\/]*)" | xargs grep -o "strip_workspace_numbers yes"
#                              grep -o "strip_workspace_numbers yes" $(i3 --more-version | grep -oP "Loaded i3 config: \K([\S\/]*)")

# FIXME : Need more testing but I don't think we need the mouse handling anymore
# FIXME : Still some wiggling (workspaces in status bar) when moving from an empty window
#         - Not sure how we could solve this, we would need a hook WORKSPACE_PRE_EMPTY. 
#           When we enter the WORKSPACE_EMPTY event, the workspace has already been killed so spawning a new placeholder create the wiggling

parser = argparse.ArgumentParser('i3 Multi Monitor workspace manager')

parser.add_argument("--rename", help="Will rename all workspaces in global workspace (From dmenu input)", 
                    action="store_true")

parser.add_argument("--back_and_forth", help="Will move back and forth between current and last focused global workspace", 
                    action="store_true")

parser.add_argument("--move_to_workspace", help="Will the currently focused container to the provided workspace", 
                    type=int, default=None, choices=range(0,10))

parser.add_argument("--missing", help="Will attempt to fix missing placeholders", 
                    action="store_true")

parser.add_argument("--tmp_folder", help="Temp folder where to store workspace names", 
                    type=str, default=str(Path.home() / '.local/share/i3-multimonitor-workspaces'))


def main(args):
    i3 = Connection()

    # Retrieve the number of monitors
    i3.nb_monitor = len([o for o in i3.get_outputs() if o.active])

    # Set initial workspace
    container_tree = i3.get_tree()
    existing_workspaces = [w.name for w in container_tree.workspaces()]
    current_workspace_name_splitted = container_tree.find_focused().workspace().name.split(":")
    focused_child_id = current_workspace_name_splitted[0]
    i3.current_global_workspace_id = current_workspace_name_splitted[0][-1]
    i3.last_global_workspace_id = i3.current_global_workspace_id

    # Keep track of workspace names
    i3.tmp_folder = args.tmp_folder
    read_workspace_names_from_file(i3)

    # Keep track of spawned placeholders
    i3.spawned_placeholders = []

    # Lock to prevent multiple events cascade
    i3.focus_lock = threading.Lock()
    i3.back_and_forth_lock = threading.Lock()

    # ======================
    #   Standalone Actions
    # ======================

    # Move focused container to another global workspace (Note: Works even if no daemon running, useful for laptop)
    if args.move_to_workspace is not None:
        move_current_container_to_workspace(i3, str(args.move_to_workspace), focused_child_id, existing_workspaces)
        exit(0)

    # Verify number of monitor
    if i3.nb_monitor <= 1:
        print("Need at least 2 monitors to use global workspaces. Terminating.")
        exit(0)

    # Verify daemon status
    running_daemon_pid = get_pid_of_running_daemon()
    assert running_daemon_pid is not None, "[ERROR] No daemon running"
    assert '\n' not in running_daemon_pid, "[ERROR] Daemon already running"

    # Rename global workspace
    if args.rename:
        send_rename_signal_to_daemon(running_daemon_pid)
        exit(0)

    # Alt-Tab like between global workspaces
    # FIXME : This should also work even if the daemon is not running. Although, as it is implemented, won't be that straightforward
    if args.back_and_forth:
        send_back_and_forth_signal_to_daemon(running_daemon_pid)
        exit(0)

    # Show missing placeholders
    if args.missing:
        update_spawned_placeholder_windows_list(i3)
        show_missing_placeholders(i3, existing_workspaces)
        exit(0)

    # ======================
    #  Multi Monitor Daemon
    # ======================

    # We make sure that no empty_workspace placeholders are left over from previous run 
    # (Can only happen if we receive SIGKILL or SIGSTOP, otherwise placeholders would have been killed on exit)
    clear_all_placeholders(i3)

    # Rewrite workspace names to reflect i3.global_workspace_names content
    rewrite_workspace_names(i3, existing_workspaces)

    # Focusing current global workspace and creating placeholders
    initial_child_ids = [f'{i}{i3.current_global_workspace_id}' if i > 0 else i3.current_global_workspace_id for i in range(i3.nb_monitor)]
    create_placeholder_windows(i3, initial_child_ids)
    focus_workspaces(i3, initial_child_ids, focus_last=focused_child_id)

    show_missing_placeholders(i3, existing_workspaces)

    # Signal handler for workspace renaming
    set_rename_handler(i3, rename_current_workspace)

    # Signal handler for workspace back and forth
    set_back_and_forth_handler(i3, do_workspace_back_and_forth)

    # Clean exit handling (will kill placeholders on exit)
    setup_exit_signal_handling(i3)

    # Setup i3 event handlers
    i3.on(Event.WORKSPACE_FOCUS, on_workspace_focus)

    print("============================================")
    print(" i3 Multi Monitor Workspace manager running")
    print("============================================")

    # Start event handling loop
    i3.main()


# Focus event handler
def on_workspace_focus(i3_inst, event):
    from_workspace = event.old.name
    from_workspace_id = from_workspace.split(':')[0]
    to_workspace = event.current.name
    to_workspace_id = to_workspace.split(":")[0]
    changing_global_workspace = i3_inst.current_global_workspace_id != to_workspace_id[-1]


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

        # Keep track of last global workspace
        i3_inst.last_global_workspace_id = i3_inst.current_global_workspace_id
        i3_inst.current_global_workspace_id = new_global_workspace_id

        # Individual workspace ids
        new_workspace_child_ids = [f"{i}{new_global_workspace_id}" if i > 0 else f"{new_global_workspace_id}" for i in range(i3_inst.nb_monitor)]
        old_workspace_child_ids = [f"{i}{old_global_workspace_id}" if i > 0 else f"{old_global_workspace_id}" for i in range(i3_inst.nb_monitor)]
        newly_focused_workspace_child_id = f"{from_workspace_id[0]}{new_global_workspace_id}" if len(from_workspace_id) > 1 else new_global_workspace_id

        # Check if the old global workspace is empty
        i3_tree = i3_inst.get_tree()
        existing_workspaces = i3_tree.workspaces()
        nb_container_in_old_workspace = sum([len(w.descendants()) for w in existing_workspaces if w.name.split(":")[0] in old_workspace_child_ids])


        # If all old workspaces are empty, kill placeholders
        if nb_container_in_old_workspace == 0:
            kill_global_workspace(i3_inst, old_workspace_child_ids)
        
        # If the placeholder windows exists in the old workspace, show them
        elif f'empty_workspace_{old_workspace_child_ids[0]}' in i3_inst.spawned_placeholders:
            show_placeholder_windows(i3_inst, old_workspace_child_ids)

            # Child workspace got deleted (Was focused & empty), got recreated with placeholder, let's rename
            if from_workspace not in [w.name for w in existing_workspaces]:
                i3_inst.command(f'rename workspace {from_workspace.split(":")[0]} to {from_workspace}')

        # If placeholders windows for the new workspace are not spawned, create them
        if f'empty_workspace_{new_workspace_child_ids[0]}' not in i3_inst.spawned_placeholders:
            create_placeholder_windows(i3_inst, new_workspace_child_ids)

        # Focus all workspaces belonging to the new global workspace
        #print(f"{to_workspace_id} -- {same_monitor_target_workspace}")
        focus_workspaces(i3_inst, new_workspace_child_ids, focus_last=newly_focused_workspace_child_id)

        # Reset mouse position
        set_mouse_position(initial_mouse_position[0], initial_mouse_position[1])

        # Unlock workspace change in 40 ms 
        # This prevent event overloading when changing workspaces super fast
        threading.Timer(0.04, i3_inst.focus_lock.release).start()


if __name__ == "__main__":
    args = parser.parse_args()
    main(args)
