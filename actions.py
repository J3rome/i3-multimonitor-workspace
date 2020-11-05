from collections import defaultdict
import os
import threading

# FIXME : Both rename function could probably be merged...

def dmenu_prompt(prompt, default_val=""):
    dmenu_cmd = f'echo "{default_val}" | dmenu -p "{prompt}"'
    process = os.popen(dmenu_cmd)
    user_input = process.read().strip()

    if user_input == default_val:
        # Nothing was entered in the dmenu input
        user_input = ""
    process.close()

    return user_input


# Standalone actions
def rename_current_workspace(i3_inst, splitted_workspace_name):
    focused_workspace_id = splitted_workspace_name[0]
    global_workspace_id = focused_workspace_id[-1]
    workspace_ids = [f"{i}{global_workspace_id}" if i > 0 else f"{global_workspace_id}" for i in range(i3_inst.nb_monitor)]

    separator_count = len(splitted_workspace_name) - 1

    focused_workspace_name_global_id = ""
    focused_workspace_custom_name = ""

    if separator_count == 1:
        if splitted_workspace_name[1] == global_workspace_id:
            focused_workspace_name_global_id = global_workspace_id
        else:
            focused_workspace_custom_name = splitted_workspace_name[1]
    elif separator_count > 1:
        focused_workspace_name_global_id = splitted_workspace_name[1]
        focused_workspace_custom_name = ":".join(splitted_workspace_name[2:])

    new_name = dmenu_prompt("Rename current workspace to :")

    rename_cmd = ""
    for workspace_id in workspace_ids:
        workspace_selector = f'"{workspace_id}:{global_workspace_id}"' if len(focused_workspace_name_global_id) > 0 else workspace_id

        if len(focused_workspace_custom_name) > 0:
            if workspace_selector[-1] == '"':
                workspace_selector = workspace_selector[:-1]

            workspace_selector += f':{focused_workspace_custom_name}"'

            if workspace_selector[0] != '"':
                workspace_selector = '"' + workspace_selector

        rename_to = f'"{workspace_id}:{global_workspace_id}' if i3_inst.rewrite_workspace_names else workspace_id
        rename_to += f":{new_name}" if len(new_name) > 0 else ""
        if i3_inst.rewrite_workspace_names:
            rename_to += '"'

        rename_cmd += f'rename workspace {workspace_selector} to {rename_to};' # FIXME : Why does 'rename workspace number X to YYY' doesn't work ?

        # FIXME : For some reason, we lose focus to certain workspaces when we call dmenu (We don't get a focused event tho) -- MIGHT NOT BE RELATED TO DMENU, might be just renaming...
        #         Clicking on another monitor will result in changing to a different workspace (As if the clicked monitor belong to another global workspace)
        #         We refocus the workspaces
        if workspace_id != focused_workspace_id:
            rename_cmd += f" workspace number {workspace_id}; "

    # Focus the previously focused workspace last
    rename_cmd += f" workspace number {focused_workspace_id}; "

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


def move_current_container_to_workspace(i3_inst, to_workspace_global_id, current_workspace_name_splitted):
    current_workspace_id = current_workspace_name_splitted[0]
    move_to = to_workspace_global_id if len(current_workspace_id) == 1 else f'{current_workspace_id[0]}{to_workspace_global_id}'

    i3_inst.command(f"move to workspace number {move_to}")


# TODO : Check if strip_workspace_numbers yes is present in config
#        If so, rename workspaces to show only Global workspace id (8,18,28 -> 8,8,8)
#              Should be renamed/named correctly when creating workspaces
#        Should also have an option to remove numbers from our own workspace names
#           If option is False, we should keep 8:NewName for all workspaces inside a global workspace
#           If True, no number identifier
#
#       Get config file path : i3 --more-version | grep -oP "Loaded i3 config: \K([\S\/]*)" | xargs grep -o "strip_workspace_numbers yes"
#                              grep -o "strip_workspace_numbers yes" $(i3 --more-version | grep -oP "Loaded i3 config: \K([\S\/]*)")


def rewrite_workspace_names(i3_inst, workspace_names, focus_last):
    rewrite_workspace_cmd = ""
    for workspace_name in workspace_names:

        #rewrite_workspace_cmd += f'rename workspace "{workspace_name}" to {workspace_name.split(":")[0]}; '
        #continue
        splitted_name = workspace_name.split(":")
        nb_separator = len(splitted_name) - 1

        if nb_separator == 0 and i3_inst.rewrite_workspace_names:
            # No global id or custom name in workspace
            global_workspace_id = workspace_name[-1]
            rewrite_workspace_cmd += f'rename workspace {workspace_name} to "{workspace_name}:{global_workspace_id}" ; '

        elif nb_separator == 1:
            # Got either a global id or a custom name in workspace name
            global_workspace_id = splitted_name[0][-1]

            if splitted_name[-1] != global_workspace_id and i3_inst.rewrite_workspace_names:
                    # The text after the ':' correspond to a workspace name. Need to add the global_id
                    rewrite_workspace_cmd += f'rename workspace "{workspace_name}" to "{splitted_name[0]}:{global_workspace_id}:{splitted_name[-1]}" ; '

        elif nb_separator == 2 and not i3_inst.rewrite_workspace_names:
            # We got a global id & a custom name. Remove the global_id
            rewrite_workspace_cmd += f'rename workspace "{workspace_name}" to "{splitted_name[0]}:{splitted_name[-1]}" ; '

    global_id = focus_last[-1]
    workspaces_to_focus = {f"{i}{global_id}" if i > 0 else f"{global_id}" for i in range(i3_inst.nb_monitor)} - {focus_last}

    for workspace_id in workspaces_to_focus:
        rewrite_workspace_cmd += f'workspace number {workspace_id} ; '
    rewrite_workspace_cmd += f'workspace number {focus_last} ; '

    i3_inst.command(rewrite_workspace_cmd)
