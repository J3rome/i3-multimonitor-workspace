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

from actions import rename_current_workspace, rewrite_workspace_names, move_current_container_to_workspace
from misc import get_mouse_position, set_mouse_position, setup_exit_signal_handling, clear_all_placeholders
from misc import get_pid_of_running_daemon, send_back_and_forth_signal_to_daemon, set_back_and_forth_handler
from misc import set_rename_handler, send_rename_signal_to_daemon

# FIXME : Sometime when clicking on another workspace name in the status bar, the name of some workspace is lost...
# FIXME : Keep track of workspace name in the daemon. This way if a workspace get killed and we pop it again, the name should stay there. Might be worth implementing using files for persistence. This way we don't loose renaming on reboot

# FIXME : When clicking on another workspace in the status bar (In another workspace than the one focused), the wrong monitor get focused... Not sure how to distinguish between click tho..
# FIXME : Need more testing but I don't think we need the mouse handling anymore
# FIXME : If somehow a workspace get deleted and we recreate it, we should look at its brother workspaces names. If a custom name is set, set the same instead of just setting the global id as we do on a normal new workspace
# FIXME : When switching 2 fast and the second workspace is empty, it might get erased
# TODO : Add option for workspaces that should always be present
# FIXME : When moving a container to a new workspace (Alt+Shift+7 when workspace 7 doesn't exist), Only the workspace on the main monitor will be created. Not a big issue, when focusing the newly created workspace the other workspaces will be created.
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

# TODO : Check if strip_workspace_numbers yes is present in config
#       Get config file path : i3 --more-version | grep -oP "Loaded i3 config: \K([\S\/]*)" | xargs grep -o "strip_workspace_numbers yes"
#                              grep -o "strip_workspace_numbers yes" $(i3 --more-version | grep -oP "Loaded i3 config: \K([\S\/]*)")


parser = argparse.ArgumentParser('i3 Multi Monitor workspace manager')

parser.add_argument("--rename", help="Will rename all workspaces in global workspace (From dmenu input)", 
                    action="store_true")

parser.add_argument("--back_and_forth", help="Will move back and forth between current and last focused global workspace", 
                    action="store_true")

parser.add_argument("--move_to_workspace", help="Will the currently focused container to the provided workspace", 
                    type=int, default=None, choices=range(0,11))


# Placeholder windows handling
def create_placeholder_windows(i3_inst, child_workspace_ids):
    create_placeholder_cmd = ""
    for workspace_id in child_workspace_ids:
        class_name = f"empty_workspace_{workspace_id}"
        create_placeholder_cmd += f"exec --no-startup-id i3-sensible-terminal --name '{class_name}'; "
        i3_inst.spawned_placeholders.append(class_name)

    i3_inst.command(create_placeholder_cmd)


def show_placeholder_windows(i3_inst, child_workspace_ids):
    global_workspace_id = child_workspace_ids[0][-1]
    workspace_name = i3.global_workspace_names[global_workspace_id] if len(i3.global_workspace_names[global_workspace_id]) > 0 else None

    show_placeholders_cmd = ""
    for workspace_id in child_workspace_ids:
        show_placeholders_cmd += f'[instance="empty_workspace_{workspace_id}$"] move to workspace number {workspace_id}; '

    i3_inst.command(show_placeholders_cmd)


def focus_workspaces(i3_inst, child_workspace_ids, focused_workspace, focus_last):
    global_workspace_id = child_workspace_ids[0][-1]
    workspace_name = i3.global_workspace_names[global_workspace_id] if len(i3.global_workspace_names[global_workspace_id]) > 0 else None

    # No need to refocus the workspace that triggered the WORKSPACE_FOCUS event, we just need to hide the placeholder
    focus_workspace_cmd = f'[instance="empty_workspace_{focused_workspace}$"] move to scratchpad; '

    for workspace_id in child_workspace_ids:
        if workspace_id != focus_last and workspace_id != focused_workspace:
            focus_workspace_cmd += f'workspace {workspace_id}:{global_workspace_id}'

            if workspace_name:
                focus_workspace_cmd += f':{workspace_name}'

            focus_workspace_cmd += f'; [instance="empty_workspace_{workspace_id}$"] move to scratchpad; '

    # Focus last the workspace on the same monitor
    focus_workspace_cmd += f'workspace {focus_last}:{global_workspace_id}'
    if workspace_name:
        focus_workspace_cmd += f':{workspace_name}'

    focus_workspace_cmd += f'; [instance="empty_workspace_{focus_last}$"] move to scratchpad; '

    i3_inst.command(focus_workspace_cmd)


# Workspace handling (killing/focusing)
def kill_global_workspace(i3_inst, child_workspace_ids):
    kill_placeholders_cmd = ""
    for workspace_id in child_workspace_ids:
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

        # Define which monitor should be focused (We want to keep focus on the same monitor)
        same_monitor_target_workspace = f"{from_workspace[0]}{new_global_workspace_id}" if len(from_workspace_id) == 2 else f"{new_global_workspace_id}"

        # Individual workspace ids
        new_workspace_child_ids = [f"{i}{new_global_workspace_id}" if i > 0 else f"{new_global_workspace_id}" for i in range(i3_inst.nb_monitor)]
        old_workspace_child_ids = [f"{i}{old_global_workspace_id}" if i > 0 else f"{old_global_workspace_id}" for i in range(i3_inst.nb_monitor)]

        # Check if the old global workspace is empty
        existing_workspaces = i3_inst.get_tree().workspaces()
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
        focus_workspaces(i3_inst, new_workspace_child_ids, focused_workspace=to_workspace_id, 
                         focus_last=same_monitor_target_workspace)

        # Reset mouse position
        set_mouse_position(initial_mouse_position[0], initial_mouse_position[1])

        # Unlock workspace change in 20 ms 
        # This prevent event overloading when changing workspaces super fast
        threading.Timer(0.02, i3_inst.focus_lock.release).start()


if __name__ == "__main__":
    args = parser.parse_args()
    i3 = Connection()

    # Retrieve the number of monitors
    i3.nb_monitor = len([o for o in i3.get_outputs() if o.active])

    # Set initial workspace
    container_tree = i3.get_tree()
    current_workspace_name_splitted = container_tree.find_focused().workspace().name.split(":")
    focused_child_workspace = current_workspace_name_splitted[0]
    i3.current_global_workspace_id = current_workspace_name_splitted[0][-1]
    i3.last_global_workspace_id = i3.current_global_workspace_id

    # Keep track of spawned placeholders
    i3.spawned_placeholders = []

    # Keep track of workspace names
    # TODO : Load names from file
    i3.global_workspace_names = {str(i):"" for i in range(0, 11)}

    # Lock to prevent multiple events cascade
    i3.focus_lock = threading.Lock()
    i3.back_and_forth_lock = threading.Lock()

    # ======================
    #   Standalone Actions
    # ======================

    # Move focused container to another global workspace (Note: Works even if no daemon running)
    if args.move_to_workspace:
        move_current_container_to_workspace(i3, args.move_to_workspace, focused_child_workspace)
        exit(0)

    # Verify number of monitor
    if i3.nb_monitor <= 1:
        print("[ERROR] Need at least 2 monitors to use global workspaces. Terminating.")
        exit(0)

    # Verify daemon status
    running_daemon_pid = get_pid_of_running_daemon()
    #assert running_daemon_pid is not None, "[ERROR] No daemon running"
    #assert '\n' not in running_daemon_pid, "[ERROR] Daemon already running"

    # Rename global workspace
    if args.rename:
        send_rename_signal_to_daemon(running_daemon_pid)
        #rename_current_workspace(i3, focused_child_workspace)
        exit(0)

    # Alt-Tab like between global workspaces
    if args.back_and_forth:
        send_back_and_forth_signal_to_daemon(running_daemon_pid)
        exit(0)


    # ======================
    #  Multi Monitor Daemon
    # ======================

    # We make sure that no empty_workspace placeholders are left over from previous run 
    # (Can only happen if we receive SIGKILL or SIGSTOP, otherwise placeholders would have been killed on exit)
    clear_all_placeholders(i3)

    # Focusing current global workspace and creating placeholders
    focused_workspace_ids = [f'{i}{i3.current_global_workspace_id}' if i > 0 else i3.current_global_workspace_id for i in range(i3.nb_monitor)]
    create_placeholder_windows(i3, focused_workspace_ids)

    # FIXME : If workspaces already exists, should rename them all to fit what is in i3.global_workspace_names
    # FIXME : Verify that there is no workspace > 9 before launching the daemon
    # FIXME : Make sure we are focusing back the same workspace that was previously focused

    focus_workspace_cmd = ""
    for workspace_id in focused_workspace_ids:
        focus_workspace_cmd += f'workspace {workspace_id}:{i3.current_global_workspace_id}'

        if len(i3.global_workspace_names[i3.current_global_workspace_id]) > 0:
            focus_workspace_cmd += f':{i3.global_workspace_names[i3.current_global_workspace_id]}'

        focus_workspace_cmd += '; '

    print(focus_workspace_cmd)
    i3.command(focus_workspace_cmd)

    # Signal handler for workspace renaming
    set_rename_handler(i3)

    # Signal handler for workspace back and forth
    set_back_and_forth_handler(i3)

    # Clean exit handling (will kill placeholders on exit)
    setup_exit_signal_handling(i3)

    # Setup i3 event handlers
    i3.on(Event.WORKSPACE_FOCUS, on_workspace_focus)

    # Start event handling loop
    i3.main()

