#!/usr/bin/python
"""
Run commands on Android devices.

Uses an internal pseudoterminal to communicate with ADB shell.
"""

# Please see `pydoc adb_pty` for usage.

__all__ = ['cmd', 'root_cmd']
__author__ = "Yam Marcovic <ymarcov@gmail.com>"
__version__ = 0.1

import os
import pty
import StringIO
import sys
import time

class ShellCommand:
    """For internal use only"""

    def __init__(self):
        """Initializes the virtual terminal and necessary pipes."""
        self._pty_in, self._pty_out = pty.openpty()
        self._pipe_in, self._pipe_out = os.pipe()

    def _read_some(self, n):
        """Reads n bytes from the virtual terminal."""
        return os.read(self._pty_in, n)

    def _read_til_prompt(self):
        """Reads bytes from the virtal terminal until the shell prompt is encountered."""
        out = StringIO.StringIO()

        while True:
            chunk_size = 0x1000
            chunk = self._read_some(chunk_size).replace("\r", '')
            out.write(chunk)

            # check if encountered prompt
            if len(chunk) >= len(self._prompt):
                if chunk.endswith(self._prompt):
                    break
            else:
                out.seek(-len(self._prompt), 2)
                if out.read(len(self._prompt)) == self._prompt:
                    break

        out.seek(0)
        return out.read()[0:-len(self._prompt)]

    def _reset_prompt(self):
        """Resets the prompt and maintains it for internal use."""
        def skip_all_output():
            while self._read_some(0x1000) == 0x1000:
                pass # ignore all output up tp this point

        skip_all_output()
        self._prompt = '::____ADB_TERM____::'
        self._send('PS1=%s' % self._prompt)
        skip_all_output()

    def _send(self, cmd):
        """Sends a command to the terminal's shell and positions
        the stream right in front of its potential output."""
        os.write(self._pipe_out, "%s\r" % cmd)
        self._read_some(len(cmd) + 1)
        while self._read_some(1) != "\n":
            pass

    def _cmd(self, cmd):
        """Returns (exit_code, output_str)"""
        self._send(cmd)
        output = self._read_til_prompt()

        self._send('echo $?')
        error_output = self._read_til_prompt()

        return int(error_output), output

    def _exit(self):
        """Exits the virtual terminal's shell."""
        def exited():
            status = os.waitpid(self.pid, os.WNOHANG)[1]
            if os.WIFEXITED(status) or os.WIFSIGNALLED(status):
                self._exit_status = status
                return True
            return False

        def send_exit():
            try:
                os.write(self._pipe_out, "exit\r")
            except OSError:
                pass

        while not exited():
            send_exit()
            time.sleep(0.1)

        return os.WEXITSTATUS(self._exit_status)

    def _start_remote_shell(self):
        """Forks and runs adb shell."""
        self.pid = os.fork()

        if self.pid == 0:
            os.close(self._pipe_out)
            os.close(self._pty_in)

            os.dup2(self._pipe_in, 0)
            os.dup2(self._pty_out, 1)
            os.dup2(self._pty_out, 2)

            try:
                os.execlp('adb', 'adb', 'shell')
            finally:
                exit(1)
        else:
            os.close(self._pipe_in)
            os.close(self._pty_out)

    def run(self, cmd):
        """run(self, cmd) -> (exit_code, output_str)

        Runs the specified command.
        """
        self._start_remote_shell()
        self._reset_prompt()
        return self._cmd(cmd)

    def close(self):
        """Closes all the internal resources."""
        os.close(self._pty_in)
        os.close(self._pipe_out)

class RootShellCommand(ShellCommand):
    """For internal use only."""

    def _reset_prompt(self):
        """Runs su and then resets prompt."""
        self._read_some(0x100)
        self._send('su')
        ShellCommand._reset_prompt(self)

def cmd(cmd_str, cmd_type=ShellCommand):
    """cmd(cmd_str) -> (exit_code, output_str)

    Runs a command on the connected device.
    """
    sc = cmd_type()
    try:
        return sc.run(cmd_str)
    finally:
        sc.close()

def root_cmd(cmd_str):
    """root_cmd(cmd_str) -> (exit_code, output_str)

    Runs a command on the connected device as the root user.
    Please note that the device must be rooted.
    """
    return cmd(cmd_str, RootShellCommand)


def test_shell_access():
    """Test if running commands works for the user 'shell'."""

    ec, out = cmd('echo $USER')
    if ec != 0 or out.strip() != 'shell':
        raise Exception('Shell access failed')

def test_root_access():
    """Test if running commands works for the user 'root'."""

    ec, out = root_cmd('echo $USER')
    if ec != 0 or out.strip() != 'root':
        raise Exception('Root access failed')

if __name__ == '__main__':
    print 'Testing ADB PTY for connected device.'
    print
    print 'Testing simple shell user access.'
    test_shell_access()
    print 'Testing simple root user access.'
    test_root_access()
    print
    print 'Expecting both shell and root ids with 0 exit code for both'
    print
    print cmd('id')
    print root_cmd('id')
