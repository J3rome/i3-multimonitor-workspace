from collections import defaultdict
import os
import threading
from ipc import do_rename
from misc import dmenu_prompt


# Standalone actions
# FIXME : Make sure that we handle spaces in name correctly
def rename_current_workspace(i3_inst):
    focused_child_id = i3_inst.get_tree().find_focused().workspace().name.split(":")[0]
    current_global_id = i3_inst.current_global_workspace_id
    child_workspace_ids = [f"{i}{current_global_id}" if i > 0 else f"{current_global_id}" for i in range(i3_inst.nb_monitor)]

    new_name = dmenu_prompt("Rename current workspace to :")        # FIXME : What happen when we press ESC ??

    if new_name is None:
        # User pressed ESC
        return

    do_rename(i3_inst, new_name, current_global_id, child_workspace_ids, focused_child_id)


def do_workspace_back_and_forth(i3_inst):
    if not i3_inst.back_and_forth_lock.acquire(blocking=False):
            return

    if i3_inst.last_global_workspace_id != i3_inst.current_global_workspace_id:
        focused_workspace_id = i3_inst.get_tree().find_focused().workspace().name.split(":")[0]
        to_focus = f"{focused_workspace_id[0]}{i3_inst.last_global_workspace_id}" if len(focused_workspace_id) > 1 else i3_inst.last_global_workspace_id

        i3_inst.command(f"workspace number {to_focus}")

    threading.Timer(0.01, i3_inst.back_and_forth_lock.release).start()


# FIXME : If the to_workspace doesn't exist, rewrite the workspace names after moving the workspace (An thus creating the workspace)
#         ... Not sure it's super helpful tho, the other global workspace childs will be created only when one of its workspace is focused
def move_current_container_to_workspace(i3_inst, to_workspace_global_id, current_workspace_id, existing_workspaces):
    if current_workspace_id[-1] == to_workspace_global_id:
        # Container already in workspace
        return

    move_to = to_workspace_global_id if len(current_workspace_id) == 1 else f'{current_workspace_id[0]}{to_workspace_global_id}'

    workspace_name = i3_inst.global_workspace_names[to_workspace_global_id] if len(i3_inst.global_workspace_names[to_workspace_global_id]) > 0 else None

    workspace_selector = f'{move_to}:{to_workspace_global_id}' if i3_inst.nb_monitor > 1 else to_workspace_global_id

    if workspace_name:
        workspace_selector += f':{workspace_name}'

    i3_inst.command(f"move container to workspace {workspace_selector}")

    if move_to not in [n.split(":")[0] for n in existing_workspaces]:
        new_childs_id = [f"{i}{to_workspace_global_id}" if i > 0 else f"{to_workspace_global_id}" for i in range(i3_inst.nb_monitor)]

        # FIXME : Detect if there is a placeholder spawned, otherwise spawn it
        #         THIS WILL FUCKUP THE DAEMON, ONLY THE DAEMON KNOW WHICH WINDOWS ARE SPAWNED.
        #         THE DAEMON WILL RECREATE PLACEHOLDER ON FOCUS
        #subprocess.popen('ps -aux | grep "i3-sensible-terminal --name \'empty_workspace_{}\'$" | wc -l')

        #show_missing_placeholders(i3_inst, new_childs_id)

