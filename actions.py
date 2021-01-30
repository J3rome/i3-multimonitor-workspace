from collections import defaultdict
import os
import threading

# FIXME : Both rename function could probably be merged...

def dmenu_prompt(prompt, default_val=""):
    if type(default_val) in [list, set]:
        default_val = "\n".join(default_val)

    dmenu_cmd = f'echo "{default_val}" | dmenu -p "{prompt}"'
    process = os.popen(dmenu_cmd)
    user_input = process.read()

    if '\n' not in user_input:
        # Esc was pressed, cancel renaming
        return None
    
    user_input = user_input.strip()

    if user_input == default_val:
        # Nothing was entered in the dmenu input
        user_input = ""
    process.close()

    return user_input


# Standalone actions
# FIXME : Make sure that we handle spaces in name correctly
def rename_current_workspace(i3_inst):
    print("Rename Called !")
    focused_child_id = i3_inst.get_tree().find_focused().workspace().name.split(":")[0]
    current_global_id = i3_inst.current_global_workspace_id
    child_workspace_ids = [f"{i}{current_global_id}" if i > 0 else f"{current_global_id}" for i in range(i3_inst.nb_monitor)]

    new_name = dmenu_prompt("Rename current workspace to :")        # FIXME : What happen when we press ESC ??

    if new_name is None:
        return

    do_rename(i3_inst, new_name, current_global_id, child_workspace_ids, focused_child_id)

    i3_inst.global_workspace_names[current_global_id] = new_name


def do_rename(i3_inst, new_name, global_workspace_id, child_workspace_ids, focused_child_id=None):
    old_workspace_name = i3_inst.global_workspace_names[global_workspace_id]

    rename_cmd = ""
    for workspace_id in child_workspace_ids:
        base_workspace_selector = f'{workspace_id}:{global_workspace_id}'
        old_workspace_selector = base_workspace_selector
        new_workspace_selector = base_workspace_selector

        if len(old_workspace_name) > 0:
            old_workspace_selector += f':{old_workspace_name}'

        if len(new_name) > 0:
            new_workspace_selector +=f':{new_name}'
            
        rename_cmd += f'rename workspace {old_workspace_selector} to {new_workspace_selector}; '

        if focused_child_id and workspace_id != focused_child_id:
            # For some reason we need to focus the workspaces when renaming, otherwise we loose focus to them... Investigate
            rename_cmd += f'workspace number {workspace_id}; '

    if focused_child_id:
        # Refocus the previously focused child workspace
        rename_cmd += f'workspace number {focused_child_id};'

    print(rename_cmd)

    i3_inst.command(rename_cmd)


def do_workspace_back_and_forth(i3_inst):
    # FIXME : If we keep Alt+Tab pressed, the program become overloaded. 
    #         Probably because it receive too many signals. We should put the lock on the signal sender
    #         We could use a file as a lock
    if not i3_inst.back_and_forth_lock.acquire(blocking=False):
            return

    if i3_inst.last_global_workspace_id != i3_inst.current_global_workspace_id:
        focused_workspace_id = i3_inst.get_tree().find_focused().workspace().name.split(":")[0]
        to_focus = f"{focused_workspace_id[0]}{i3_inst.last_global_workspace_id}" if len(focused_workspace_id) > 1 else i3_inst.last_global_workspace_id

        i3_inst.command(f"workspace number {to_focus}")

    threading.Timer(0.01, i3_inst.back_and_forth_lock.release).start()


# FIXME : If the to_workspace doesn't exist, rewrite the workspace names after moving the workspace (An thus creating the workspace)
#         ... Not sure it's super helpful tho, the other global workspace childs will be created only when one of its workspace is focused
def move_current_container_to_workspace(i3_inst, to_workspace_global_id, current_workspace_id):
    move_to = to_workspace_global_id if len(current_workspace_id) == 1 else f'{current_workspace_id[0]}{to_workspace_global_id}'

    i3_inst.command(f"move container to workspace number {move_to}")

