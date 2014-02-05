import os
import platform
import subprocess
import sys
import time

class CmdException(Exception):
    pass

_decode_error_action = 'ignore'

def cmd(s, cwd=None, capture=False, ok_exit_code_list=[0], echo=False):
    """
    Executes the command "s".

    It raises an exception if the command fails to run.

    capture ... If True, it captures its output and returns it as a string.
    ok_exit_code_list ... a list of ok exit codes (otherwise cmd() raises an
    exception)
    """
    if echo:
        print s
    s = os.path.expandvars(s)
    if capture:
        out = subprocess.PIPE
    else:
        out = None
    p = subprocess.Popen(s, shell=True, stdout=out, stderr=subprocess.STDOUT,
            cwd=cwd)
    output = p.communicate()[0]
    if output:
        output = output.decode(sys.stdout.encoding, _decode_error_action)
    r = p.returncode
    if r not in ok_exit_code_list:
        raise CmdException("Command '%s' failed with err=%d. %s" % (s, r, output))
    return output


def cmd2(cmd, cwd=None):
    """
    Runs the command "cmd", mirrors everything on the screen and returns a log
    as well as the return code.
    """
    print "Running unit tests."
    print "Command:", cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, cwd=cwd)

    log = ""
    while True:
        char = p.stdout.read(1)
        if not char:
            break
        log += char
        sys.stdout.write(char)
        sys.stdout.flush()
    log = log + p.communicate()[0]
    log = log.decode(sys.stdout.encoding, _decode_error_action)
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


def get_interpreter_type(interpreter):
    # TODO: support other alternate pythons
    code = """
import sys
if hasattr(sys, 'pypy_version_info'):
    print('PyPy %s.%s.%s-%s-%s;' % sys.pypy_version_info[:])
else:
    print('Python')
    """
    cmd = '%s -c "%s"' % (interpreter, code)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    ouput = p.stdout.read()

    return ouput.strip()


def get_executable(interpreter):
    path = os.environ['PATH']
    paths = path.split(os.pathsep)
    # Add .exe extension for Windows
    if os.name == "nt":
        interpreter = os.path.splitext(interpreter)[0] + ".exe"
    if os.path.isfile(interpreter):
        return interpreter
    for p in paths:
        f = os.path.join(p, interpreter)
        if os.path.isfile(f):
            return f


def get_platform_version(interpreter):
    code = 'import sys; print(getattr(sys, \\"maxint\\", None))'
    call = '%s -c "%s"' % (interpreter, code)
    size = cmd(call, capture=True)
    if size == 'None\n':  # Python 3 doesn't have maxint, 2.5 doesn't have maxsize
        code = 'import sys; print(sys.maxsize)'
        call = '%s -c "%s"' % (interpreter, code)
        size = cmd(call, capture=True)
    size = int(size)
    if size > 2**32:
        architecture = "64-bit"
    else:
        architecture = "32-bit"
    platform_system = platform.system()
    # TODO: This doesn't recognize bin/test -C (issue #121)
    use_cache = os.getenv('SYMPY_USE_CACHE', 'yes').lower()
    executable = get_executable(interpreter)
    python_version = get_interpreter_version_info(interpreter)
    python_type = get_interpreter_type(interpreter)

    return {'executable': executable,
            'python_version': python_version,
            'platform_system': platform_system,
            'architecture': architecture,
            'use_cache': use_cache,
            'additional_info': "",
            'python_type': python_type,
    }


def get_sphinx_version():
    try:
        import sphinx
    except ImportError:
        return
    version = sphinx.__version__
    r = " %s" % version
    return {'sphinx_version': r, 'additional_info': ""}

def keep_trying(command, errors, what_did, on_except=None):
    """
    Keep trying command, using a time doubling scheme.

    Parameters
    ----------
    command - A function with no arguments to be called.  If it's just one
        line, use something like lambda: do_something().

    errors - A list of errors to catch, like (URLError,).

    what_did - A string representing what the function is doing, for use in
        the error message.  It should be in past tense, and not start with a
        capital letter. For example, "get pull request 1234".

    on_except - (Optional) A function to be run when the exception is run,
        before the error message is caught.  Should be a function that takes a
        single argument, the error that was caught.  If the function returns a
        non-None value, that is returned.  Otherwise, it retries.

    It tries `command()`, and if it raises one of the errors in `errors`, it
    prints an error message based on `what_did`, then tries again in one
    second. If it fails again, it tries again in two seconds, then four
    seconds, and so on (doubling each time).

    This "time doubling" scheme mimics other systems such as the Google
    AppEngine uploader and GMail, and is useful to give fast response time for
    minor blips, but avoids DoSing the server, which can often make the
    problem worse (e.g., if the reason the request failed is that you hit a
    quota).

    The return value is the same as the return value of `command()`, or
    `on_except()` if that was run and returned non-None.

    """
    timer = 1

    while True:
        try:
            result = command()
            break
        except errors as e:
            if on_except:
                a = on_except(e)
                if a is not None:
                    return a

            print "Could not %s, retrying in %d seconds..." % (what_did, timer)
            time.sleep(timer)
            timer *= 2

    return result
