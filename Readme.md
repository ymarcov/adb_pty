A simple Python 2.7 library to run commands on a remote Android device using ADB. The library opens a pseudoterminal in order to circumvent input redirection issues. Also, it uses `su` to open a root shell, instead of relying on a particular implementation of `su` which takes a certain set of parameters to run a command. As long as the simple command `su` gives you a root shell after you connect with `adb shell`, issuing root commands using this library should work.

**Usage:**

```python
import adb_pty

status, output = adb_pty.cmd('ls -l /')
status, output = adb_pty.root_cmd('mount -o remount,rw /')
```
