import os
import subprocess
import signal

from actions import do_workspace_back_and_forth, rename_current_workspace

# TODO : either use os or subprocess..

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
def set_back_and_forth_handler(i3_inst):
    signal.signal(signal.SIGUSR1, lambda x,y: do_workspace_back_and_forth(i3_inst))


def send_back_and_forth_signal_to_daemon(daemon_pid):
    os.kill(int(daemon_pid), signal.SIGUSR1)


def set_rename_handler(i3_inst):
    signal.signal(signal.SIGUSR2, lambda x,y: rename_current_workspace(i3_inst))


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
def get_pid_of_running_daemon():
    # FIXME : This doesn't work if the daemon is launched with parameters.. But it help grepping out the --rename and --back_and_forth processes..
    cmd = 'ps -x | grep " python.*i3-multimonitor-workspace.py$" | grep -v "/bin/sh" | awk \'{print $1}\''

    pid = subprocess.check_output(cmd, shell=True).decode().strip()

    if len(pid) > 0:
        return pid
    
    return None


def clear_all_placeholders(i3_inst):
    i3_inst.command('[instance="empty_workspace"] kill')

