import os
import platform
import subprocess
import sys

class CmdException(Exception):
    pass

def cmd(s, capture=False, ok_exit_code_list=None, echo=False):
    """
    Executes the command "s".

    It raises an exception if the command fails to run.

    capture ... If True, it captures its output and returns it as a string.
    ok_exit_code_list ... a list of ok exit codes (otherwise cmd() raises an
    exception)
    """
    if ok_exit_code_list is None:
        ok_exit_code_list = [0]
    if echo:
        print s
    s = os.path.expandvars(s)
    if capture:
        p = subprocess.Popen(s, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
        output = p.communicate()[0]
        r = p.returncode
    else:
        output = None
        r = os.system(s)
    if r not in ok_exit_code_list:
        raise CmdException("Command '%s' failed with err=%d." % (s, r))
    return output

def cmd2(cmd):
    """
    Runs the command "cmd", mirrors everything on the screen and returns a log
    as well as the return code.
    """
    print "Running unit tests."
    print "Command:", cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)

    log = ""
    while True:
        char = p.stdout.read(1)
        if not char:
            break
        log += char
        sys.stdout.write(char)
        sys.stdout.flush()
    log = log + p.communicate()[0]
    r = p.returncode

    return log, r

def get_interpreter_version_info(interpreter):
    """
    Get python version of `interpreter`
    """

    code = "import sys; print('%s.%s.%s-%s-%s' % sys.version_info[:])"
    cmd = '%s -c "%s"' % (interpreter, code)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    ouput = p.stdout.read()

    return ouput.strip()

def get_executable(interpreter):
    path = os.environ['PATH']
    paths = path.split(os.pathsep)
    if os.name == "nt":
        return get_executable_exe(interpreter)
    for p in paths:
        f = os.path.join(p, interpreter)
        if os.path.isfile(f):
            return f

def get_executable_exe(interpreter):
    """
    Get python executable path for 'nt'
    """

    code = "import sys; print(sys.executable)"
    cmd = '%s -c "%s"' % (interpreter, code)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    ouput = p.stdout.read()

    return ouput.strip()

def get_platform_version(interpreter):
    code = 'import sys; print(getattr(sys, "maxint", None))'
    call = "%s -c '%s'" % (interpreter, code)
    size = cmd(call, capture=True)
    if size == 'None\n': # Python 3 doesn't have maxint, 2.5 doesn't have maxsize
        code = 'import sys; print(sys.maxsize)'
        call = "%s -c '%s'" % (interpreter, code)
        size = cmd(call, capture=True)
    size = int(size)
    if size > 2**32:
        architecture = "64-bit"
    else:
        architecture = "32-bit"
    platform_system = platform.system()
    use_cache = os.getenv('SYMPY_USE_CACHE', 'yes').lower()
    executable = get_executable(interpreter)
    python_version = get_interpreter_version_info(interpreter)
    r  = "*Interpreter:*  %s (%s)\n" % (executable, python_version)
    r += "*Architecture:* %s (%s)\n" % (platform_system, architecture)
    r += "*Cache:*        %s\n" % use_cache
    return r

def get_sphinx_version():
    try:
        import sphinx
    except ImportError:
        return
    version = sphinx.__version__
    r = "*Sphinx version:* %s" % version
    return r