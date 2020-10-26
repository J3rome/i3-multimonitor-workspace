import os
import subprocess
import signal

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


def dmenu_prompt(prompt, default_val=""):
    dmenu_cmd = f'echo "{default_val}" | dmenu -p "{prompt}"'
    process = os.popen(dmenu_cmd)
    user_input = process.read().strip()

    if user_input == default_val:
        # Nothing was entered in the dmenu input
        user_input = ""
    process.close()

    return user_input


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