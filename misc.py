import os
import subprocess
import signal

from actions import do_workspace_back_and_forth

# TODO : either use os or subprocess..

# Mouse handling
def get_mouse_position():
    raw_out = subprocess.check_output('xdotool getmouselocation'.split(' ')).decode()
    x_y = raw_out.split(' screen')[0].split(' y:')
    x = int(x_y[0].split('x:')[-1])
    y = int(x_y[1])

    return x, y


def set_mouse_position(x, y):
    subprocess.check_output(f'xdotool mousemove {x} {y}'.split(' '))


def get_pid_of_running_daemon():
    # FIXME : This doesn't work if the daemon is launched with parameters.. But it help grepping out the --rename and --back_and_forth processes..
    cmd = 'ps -x | grep " python.*i3-multimonitor-workspace.py$" | grep -v "/bin/sh" | awk \'{print $1}\''

    process = os.popen(cmd)
    pid = process.read().strip()
    process.close()

    if len(pid) > 0:
        return pid
    
    return None


def set_back_and_forth_handler(i3_inst):
    signal.signal(signal.SIGUSR1, lambda x,y: do_workspace_back_and_forth(i3_inst))


def send_back_and_forth_signal_to_daemon(daemon_pid):
    os.kill(int(daemon_pid), signal.SIGUSR1)


def create_missing_workspaces(i3_inst, names_by_global_workspace, focused_id):
    create_workspace_cmd = ""
    for global_id in names_by_global_workspace.keys():
        if global_id == focused_id[-1]:
            continue

        if len(names_by_global_workspace[global_id]) < i3.nb_monitor:
            missing_workspaces = list({f"{i}{new_global_workspace_id}" if i > 0 else f"{new_global_workspace_id}" for i in range(i3_inst.nb_monitor)} - {n.split(":")[0] for n in names_by_global_workspace[global_id]})
            for name in missing_workspaces:
                create_workspace_cmd += f"workspace "



def clear_all_placeholders(i3_inst):
    i3_inst.command('[instance="empty_workspace"] kill')


def setup_exit_signal_handling(i3_inst):
    signals_of_interest = [signal.SIGHUP, signal.SIGINT, signal.SIGQUIT, signal.SIGTERM, signal.SIGFPE, signal.SIGILL,
                           signal.SIGSEGV, signal.SIGABRT,  signal.SIGBUS, signal.SIGSYS, signal.SIGTSTP] #signal.SIGSTOP

    def clean_exit(the_i3_inst):
        clear_all_placeholders(the_i3_inst)
        exit(0)

    for sig in signals_of_interest:
        signal.signal(sig, lambda x,y: clean_exit(i3_inst))