import os
import subprocess
import signal
import json

# Mouse handling
def get_mouse_position():
    raw_out = subprocess.check_output('xdotool getmouselocation', shell=True).decode()
    x_y = raw_out.split(' screen')[0].split(' y:')
    x = int(x_y[0].split('x:')[-1])
    y = int(x_y[1])

    return x, y


def set_mouse_position(x, y):
    subprocess.check_output(f'xdotool mousemove {x} {y}', shell=True)


# Signal handlers
def set_back_and_forth_handler(i3_inst, handler_fct):
    signal.signal(signal.SIGUSR1, lambda x,y: handler_fct(i3_inst))


def send_back_and_forth_signal_to_daemon(daemon_pid):
    os.kill(int(daemon_pid), signal.SIGUSR1)


def set_rename_handler(i3_inst, handler_fct):
    signal.signal(signal.SIGUSR2, lambda x,y: handler_fct(i3_inst))


def send_rename_signal_to_daemon(daemon_pid):
    os.kill(int(daemon_pid), signal.SIGUSR2)


def setup_exit_signal_handling(i3_inst):
    signals_of_interest = [signal.SIGHUP, signal.SIGINT, signal.SIGQUIT, signal.SIGTERM, signal.SIGFPE, signal.SIGILL,
                           signal.SIGSEGV, signal.SIGABRT,  signal.SIGBUS, signal.SIGSYS, signal.SIGTSTP] #signal.SIGSTOP

    def clean_exit(the_i3_inst):
        clear_all_placeholders(the_i3_inst)
        exit(0)

    for sig in signals_of_interest:
        signal.signal(sig, lambda x,y: clean_exit(i3_inst))


# Others
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

    
def get_pid_of_running_daemon():
    # FIXME : This doesn't work if the daemon is launched with parameters.. But it help grepping out the --rename and --back_and_forth processes..
    cmd = 'ps -x | grep " python.*i3-multimonitor-workspace.py$" | grep -v "/bin/sh" | awk \'{print $1}\''

    pid = subprocess.check_output(cmd, shell=True).decode().strip()

    if len(pid) > 0:
        return pid
    
    return None


def clear_all_placeholders(i3_inst):
    i3_inst.command('[instance="empty_workspace"] kill')


def read_workspace_names_from_file(i3_inst, filename="workspace_names.json"):
    full_path = f"{i3_inst.tmp_folder}/{filename}"
    names = {str(i):"" for i in range(0, 10)}   # Default values

    if not os.path.exists(i3_inst.tmp_folder):
        os.makedirs(i3_inst.tmp_folder)

    elif os.path.exists(full_path):
        try:
            with open(full_path, 'r') as f:
                loaded_names = json.load(f)

            if len(loaded_names) < 10:
                raise Exception('Invalid config, must contains 1 key for each workspace')

            names = loaded_names

        except:
            # Malformed json, rewrite config to default value
            os.remove(full_path)

    # Either the file doesn't exist or the config was invalid. We write default values
    i3_inst.global_workspace_names = names
    write_workspace_names_to_file(i3_inst)

    return names


def write_workspace_names_to_file(i3_inst, filename="workspace_names.json"):
    full_path = f"{i3_inst.tmp_folder}/{filename}"
    with open(full_path, 'w') as f:
        json.dump(i3_inst.global_workspace_names, f, indent=2)

