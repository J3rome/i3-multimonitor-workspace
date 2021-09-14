import time 

from misc import write_workspace_names_to_file

# Placeholder windows handling
def create_placeholder_windows(i3_inst, child_workspace_ids):
    created = False
    create_placeholder_cmd = ""
    for workspace_id in child_workspace_ids:
        class_name = f"empty_workspace_{workspace_id}"
        if class_name not in i3_inst.spawned_placeholders:
            create_placeholder_cmd += f"exec --no-startup-id i3-sensible-terminal --name '{class_name}'; "
            i3_inst.spawned_placeholders.append(class_name)
            created = True
            print(class_name)

    i3_inst.command(create_placeholder_cmd)

    return created


def show_placeholder_windows(i3_inst, child_workspace_ids):
    global_workspace_id = child_workspace_ids[0][-1]
    workspace_name = i3_inst.global_workspace_names[global_workspace_id] if len(i3_inst.global_workspace_names[global_workspace_id]) > 0 else None

    show_placeholders_cmd = ""
    for workspace_id in child_workspace_ids:
        workspace_selector = f'{workspace_id}:{global_workspace_id}'

        if workspace_name:
            workspace_selector += f':{workspace_name}'

        show_placeholders_cmd += f'[instance="empty_workspace_{workspace_id}$"] move to workspace {workspace_selector}; '

    i3_inst.command(show_placeholders_cmd)


def update_spawned_placeholder_windows_count(i3_inst):
    i3_inst.spawned_placeholders = [w.window_instance for w in i3_inst.get_tree().descendants() if w.window_instance and w.window_instance.startswith('empty_workspace')]


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
        workspace_selector_splitted_len = len(workspace_selector_splitted)
        workspace_id = workspace_selector_splitted[0]
        global_id = workspace_id[-1]

        # If there is 2 separator, the last field is the name
        workspace_name = workspace_selector_splitted[-1] if workspace_selector_splitted_len == 3 else ""

        if i3_inst.global_workspace_names[global_id] != workspace_name or workspace_selector_splitted_len == 1:
            new_selector = f'{workspace_id}:{global_id}'

            if len(i3_inst.global_workspace_names[global_id]) > 0:
                new_selector += f':{i3_inst.global_workspace_names[global_id]}'

            rewrite_cmd += f'rename workspace {workspace_selector} to {new_selector}; '

    i3_inst.command(rewrite_cmd)


def show_missing_placeholders(i3_inst, existing_workspaces):
    global_ids = {w.split(":")[0][-1] for w in existing_workspaces} - {i3_inst.current_global_workspace_id}

    for global_id in global_ids:
        child_ids = [f'{i}{global_id}' if i > 0 else global_id for i in range(i3_inst.nb_monitor)]

        created = create_placeholder_windows(i3_inst, child_ids)

        if created:
            print("Waiting for ", child_ids)
            # Need to wait for the placeholders to be spawned
            time.sleep(0.25)

        show_placeholder_windows(i3_inst, child_ids)