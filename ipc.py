from misc import write_workspace_names_to_file

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
    workspace_name = i3_inst.global_workspace_names[global_workspace_id] if len(i3_inst.global_workspace_names[global_workspace_id]) > 0 else None

    show_placeholders_cmd = ""
    for workspace_id in child_workspace_ids:
        show_placeholders_cmd += f'[instance="empty_workspace_{workspace_id}$"] move to workspace number {workspace_id}; '

    i3_inst.command(show_placeholders_cmd)


# Workspace handling (focusing/renaming/killing)
def focus_workspaces(i3_inst, child_workspace_ids, focus_last):
    global_workspace_id = child_workspace_ids[0][-1]
    workspace_name = i3_inst.global_workspace_names[global_workspace_id] if len(i3_inst.global_workspace_names[global_workspace_id]) > 0 else None

    # No need to refocus the workspace that triggered the WORKSPACE_FOCUS event, we just need to hide the placeholder
    #focus_workspace_cmd = f'[instance="empty_workspace_{focus_last}$"] move to scratchpad; '
    focus_workspace_cmd = ""

    for workspace_id in child_workspace_ids:
        if workspace_id != focus_last:
            workspace_selector = f'{workspace_id}:{global_workspace_id}'

            if workspace_name:
                workspace_selector += f':{workspace_name}'

            focus_workspace_cmd += f'workspace {workspace_selector}; [instance="empty_workspace_{workspace_id}$"] move to scratchpad; '

    # Focus last the workspace on the same monitor
    workspace_selector = f'{focus_last}:{global_workspace_id}'

    if workspace_name:
        workspace_selector += f':{workspace_name}'

    focus_workspace_cmd += f'workspace {workspace_selector}; [instance="empty_workspace_{focus_last}$"] move to scratchpad; '

    i3_inst.command(focus_workspace_cmd)


def kill_global_workspace(i3_inst, child_workspace_ids):
    kill_placeholders_cmd = ""
    for workspace_id in child_workspace_ids:
        class_name = f'empty_workspace_{workspace_id}'
        kill_placeholders_cmd += f'[instance="{class_name}$"] kill;'
        i3_inst.spawned_placeholders.remove(class_name)

    i3_inst.command(kill_placeholders_cmd)


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

    # Save new name to file
    i3_inst.global_workspace_names[global_workspace_id] = new_name
    write_workspace_names_to_file(i3_inst)

    i3_inst.command(rename_cmd)


def rewrite_workspace_names(i3_inst, workspace_selectors):

    rewrite_cmd = ""
    for workspace_selector in workspace_selectors:
        workspace_selector_splitted = workspace_selector.split(":")
        workspace_id = workspace_selector_splitted[0]
        workspace_name = workspace_selector_splitted[-1] if len(workspace_selector_splitted) == 3 else ""
        global_id = workspace_id[-1]

        if i3_inst.global_workspace_names[global_id] != workspace_name:
            new_selector = f'{workspace_id}:{global_id}'

            if len(i3_inst.global_workspace_names[global_id]) > 0:
                new_selector += f':{i3_inst.global_workspace_names[global_id]}'

            rewrite_cmd += f'rename workspace {workspace_selector} to {new_selector}; '

    i3_inst.command(rewrite_cmd)
