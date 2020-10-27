from misc import dmenu_prompt


# Standalone actions
def rename_current_workspace(i3_inst):
    splitted_workspace_name = i3_inst.current_workspace_name.split(":")
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

    new_name = dmenu_prompt("Rename current workspace to :", splitted_workspace_name[-1])

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

        # FIXME : For some reason, we lose focus to certain workspaces when we call dmenu (We don't get a focused event tho)
        #         Clicking on another monitor will result in changing to a different workspace (As if the clicked monitor belong to another global workspace)
        #         We refocus the workspaces
        if workspace_id != focused_workspace_id:
            rename_cmd += f" workspace number {workspace_id}; "

    # FIXME : Is the mouse jittering ? Might need to save and reset mouse
    # Focus the previously focused workspace last
    rename_cmd += f" workspace number {focused_workspace_id}; "

    i3_inst.command(rename_cmd)


# TODO : Check if strip_workspace_numbers yes is present in config
#        If so, rename workspaces to show only Global workspace id (8,18,28 -> 8,8,8)
#              Should be renamed/named correctly when creating workspaces
#        Should also have an option to remove numbers from our own workspace names
#           If option is False, we should keep 8:NewName for all workspaces inside a global workspace
#           If True, no number identifier
#
#       Get config file path : i3 --more-version | grep -oP "Loaded i3 config: \K([\S\/]*)" | xargs grep -o "strip_workspace_numbers yes"
#                              grep -o "strip_workspace_numbers yes" $(i3 --more-version | grep -oP "Loaded i3 config: \K([\S\/]*)")


def rewrite_workspace_names(i3_inst, workspace_names):
    rewrite_workspace_cmd = ""
    for workspace_name in workspace_names:

        #rewrite_workspace_cmd += f'rename workspace "{workspace_name}" to {workspace_name.split(":")[0]}; '
        #continue

        nb_separator = workspace_name.count(':')

        if nb_separator == 0 and i3_inst.rewrite_workspace_names:
            # No global id or custom name in workspace
            global_workspace_id = workspace_name[-1]
            rewrite_workspace_cmd += f'rename workspace {workspace_name} to "{workspace_name}:{global_workspace_id}" ; '

        elif nb_separator == 1:
            # Got either a global id or a custom name in workspace name
            splitted_name = workspace_name.split(":")
            global_workspace_id = splitted_name[0][-1]

            if splitted_name[-1] != global_workspace_id and i3_inst.rewrite_workspace_names:
                    # The text after the ':' correspond to a workspace name. Need to add the global_id
                    rewrite_workspace_cmd += f'rename workspace "{workspace_name}" to "{splitted_name[0]}:{global_workspace_id}:{splitted_name[-1]}" ; '

        elif nb_separator == 2 and not i3_inst.rewrite_workspace_names:
            # We got a global id & a custom name. Remove the global_id
            splitted_name = workspace_name.split(":")

            rewrite_workspace_cmd += f'rename workspace "{workspace_name}" to "{splitted_name[0]}:{splitted_name[-1]}" ; '

        # TODO : Focus back current workspace ?
    i3_inst.command(rewrite_workspace_cmd)
