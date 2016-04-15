from path import path

TMP_PATH = path('/tmp/xblock_scilab/')

# Local ws03
SCLAB_SERVER_URL = 'http://192.168.33.1:8003'
SCLAB_SERVER_PORT = 8003
SCILAB_EXEC = path("/opt/scilab-5.5.2/bin/scilab-adv-cli")
SCILAB_HOME = path("/opt/scilab-5.5.2/")

# Server cloud cde
# SCLAB_SERVER_URL = 'http://192.168.4.50:8003'
# SCLAB_SERVER_PORT = 8003
# SCILAB_EXEC = path("/usr/bin/scilab-adv-cli")
# SCILAB_HOME = path("/usr")

# lms server
# SCLAB_SERVER_URL = 'http://127.0.0.1:8003'
# SCLAB_SERVER_PORT = 8003
# SCILAB_EXEC = path("/ifmo/app/scilab-5.5.2/bin/scilab-adv-cli")
# SCILAB_HOME = path("/ifmo/app/scilab-5.5.2")

SCILAB_STUDENT_SCRIPT = "solution.sce"
SCILAB_INSTRUCTOR_SCRIPT = "check.sce"
SCILAB_GENERATE_SCRIPT = "generate.sce"
SCILAB_EXEC_SCRIPT = "disp('Execution started'); " \
                     "chdir('{pwd}'); " \
                     "exec('{filename}'); " \
                     "disp('Finish token: {token}'); " \
                     "exit();"

XQUEUE_INTERFACE = {
    'url': 'http://localhost/',
    'login': 'login',
    'password': 'password',
    'queue': 'queue'
}

POLL_INTERVAL = 5
