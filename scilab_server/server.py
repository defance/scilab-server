# -*- coding=utf-8 -*-

import base64
import logging
import logging.config
import os.path
import requests
import tempfile
import time
import zipfile

from cStringIO import StringIO
from xqueue_api import XQueueSession
from xqueue_api.xsubmission import XSubmission

from scilab_server.executable import spawn_scilab
from scilab_server.settings import *
from xqueue.xgeneration import XGeneration

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


def cleanup(cwd):
    cwd.rmtree_p()


def make_result(msg=None, grade=0.0):
    return {
        'msg': msg,
        'grade': grade,
    }


def make_feedback(msg_type=None, message=None, output_execute=None, output_check=None, pregenerated=None):
    result = {}
    if msg_type is not None:
        result['msg_type'] = msg_type
    if message is not None:
        result['message'] = message
    if output_execute is not None:
        result['output_execute'] = unicode(output_execute, errors='replace')
    if output_check is not None:
        result['output_check'] = unicode(output_check, errors='replace')
    if pregenerated is not None:
        result['pregenerated'] = pregenerated
    return json.dumps(result)


def get_raw_archive(data, archive):
    archive_path = path(data.get('%s_name' % archive))
    archive_raw = StringIO(base64.decodestring(data.get(archive)))
    return archive_path, archive_raw


def get_archives(url):
    return json.loads(requests.get(url).text)


def do_generate(xgeneration):

    # Archives
    archives = get_archives(xgeneration.archive_url)
    instructor_filename, instructor_file = get_raw_archive(archives, 'instructor_archive')
    grader_payload = json.loads(xgeneration.grader_payload)

    # Полный рабочий путь в системе, со временной директорией, сразу вычистим
    # TODO: generate RANDOM path using guid
    TMP_PATH.makedirs_p()
    full_path = tempfile.mkdtemp(prefix=TMP_PATH)

    # Подчистка с самого начала нам не нужна, поскольку можно положиться на то,
    # что будет создан уникальный путь
    # cleanup(cwd=full_path)

    try:
        instructor_archive = zipfile.ZipFile(instructor_file)
        instructor_archive.extractall(full_path)
    except Exception:
        return xgeneration.set_generation_result(False, "Archive read/extract error")

    filename = full_path / SCILAB_GENERATE_SCRIPT

    # Допишем функцию выхода, на всякий случай
    with open(filename, "a") as source_file:
        source_file.write("\nexit();\n")

    generate_code = spawn_scilab(filename, timeout=grader_payload.get('time_limit_generate') or DEFAULT_TIMEOUT)

    try:
        with open(full_path + '/generate_output', 'r') as f:
            pregenerated = f.read()
    except IOError:
        return xgeneration.set_generation_result(False, "Pregenerated read error")

    xgeneration.set_generation_result(True, pregenerated)

    return xgeneration


def do_check(xsubmission):

    xsubmission.set_grade(grader=GRADER_ID)

    result = {}

    # Dicts
    student_input = json.loads(xsubmission.student_response)
    grader_payload = json.loads(xsubmission.grader_payload)

    # Archives
    data = get_archives(student_input.get('archive_64_url'))

    student_filename, student_file = get_raw_archive(data, 'user_archive')
    instructor_filename, instructor_file = get_raw_archive(data, 'instructor_archive')

    # Полный рабочий путь в системе, со временной директорией, сразу вычистим
    TMP_PATH.makedirs_p()
    full_path = tempfile.mkdtemp(prefix=TMP_PATH)

    # Подчистка с самого начала нам не нужна, поскольку можно положиться на то,
    # что будет создан уникальный путь
    # cleanup(cwd=full_path)

    # Извлекаем архив студента
    try:
        student_archive = zipfile.ZipFile(student_file)
        student_archive.extractall(full_path)
    except (zipfile.BadZipfile, IOError):
        feedback = make_feedback(message='SAE: Не удалось открыть архив с ответом. Загруженный файл должен быть .zip.',
                                 msg_type='error')
        return xsubmission.set_grade(feedback=feedback, success=False)

    # Процессу разрешено выполняться только 2 секунды
    filename = full_path / SCILAB_STUDENT_SCRIPT

    if os.path.exists(filename):

        # Допишем функцию выходна, на всякий случай
        with open(filename, "a") as source_file:
            source_file.write("exit();")

        student_code = spawn_scilab(filename, timeout=grader_payload.get('time_limit_execute') or DEFAULT_TIMEOUT)
        if student_code.get('return_code') == -1:
            feedback = make_feedback(message='TL: Превышен лимит времени', msg_type='error',
                                     pregenerated=grader_payload.get('pregenerated'),
                                     output_execute=student_code['output'])
            return xsubmission.set_grade(feedback=feedback, success=False)

    else:
        student_code = {
            'return_code': -2,
            'output': None,
        }
        logging.debug("No executable found in student answer (does not exists): %s" % filename)

    # Запишем pregenerated, если он вообще есть
    if grader_payload.get('pregenerated') is not None:
        with open(full_path / "generate_output", "w") as f:
            f.write(grader_payload['pregenerated'])

    try:
        instructor_archive = zipfile.ZipFile(instructor_file)
        instructor_archive.extractall(full_path)
    except (zipfile.BadZipfile, IOError):
        feedback = make_feedback(message='IAE: Не удалось открыть архив инструктора.', msg_type='error')
        return xsubmission.set_grade(feedback=feedback, success=False)

    filename = full_path / SCILAB_INSTRUCTOR_SCRIPT

    # Допишем функцию выхода, на всякий случай
    with open(filename, "a") as source_file:
        source_file.write("\nexit();\n")

    checker_code = spawn_scilab(filename, timeout=grader_payload.get('time_limit_check') or DEFAULT_TIMEOUT)
    if checker_code.get('return_code') == -1:
        feedback = make_feedback(message='TL: Превышен лимит времени', msg_type='error',
                                 pregenerated=grader_payload.get('pregenerated'),
                                 output_execute=student_code['output'],
                                 output_check=checker_code['output'])
        return xsubmission.set_grade(feedback=feedback, success=False)

    try:
        f = open(full_path / 'check_output')
        result_grade = float(f.readline().strip())
        result_message = f.readline().strip()
    except IOError:
        feedback = make_feedback(message='COE: Не удалось определить результат проверки.', msg_type='error',
                                 output_execute=student_code['output'],
                                 output_check=checker_code['output'])
        return xsubmission.set_grade(feedback=feedback, success=False)

    feedback = make_feedback(message=result_message, msg_type='success',
                             pregenerated=grader_payload.get('pregenerated'),
                             output_execute=student_code['output'],
                             output_check=checker_code['output'])
    return xsubmission.set_grade(grade=result_grade, feedback=feedback, correctness=True, success=True)


def setup_logging(
    default_path=LOGGING_DEFAULT_PATH,
    default_level=LOGGING_DEFAULT_LEVEL,
    env_key=LOGGING_ENV_KEY
):
    """
    Setup logging configuration
    """
    config_path = default_path
    value = os.getenv(env_key, None)
    if value:
        config_path = path(value)
    if config_path.exists():
        with open(config_path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def main():

    setup_logging()

    logger.info("Starting server...")
    logger.info("CONFIG_ROOT = %s" % CONFIG_ROOT)
    logger.info("CONFIG_FILE = %s" % CONFIG_FILE)
    logger.info("Opening env file: %s" % (CONFIG_ROOT / CONFIG_FILE))
    logger.info("xqueue url = %s" % XQUEUE_INTERFACE['url'])

    # Начинаем работу сервера
    while True:
        xsession = XQueueSession(base_url=XQUEUE_INTERFACE['url'],
                                 username=XQUEUE_INTERFACE['login'],
                                 password=XQUEUE_INTERFACE['password'],
                                 queue=XQUEUE_INTERFACE['queue'],
                                 autoconnect=True)
        length_result, length = xsession.get_len()
        if length_result and length:

            logger.info("Non zero length, retrieve submission")

            xobject_result, xobject = xsession.get_xobject()
            if xobject_result:

                body = json.loads(xobject.body)
                method = body.get('method', None)
                logger.info('Received method: {method}'.format(method=method))

                if method == u'check':
                    result = do_check(XSubmission.create_from_xobject(xobject))

                elif method == u'generate':
                    result = do_generate(XGeneration.create_from_xobject(xobject))

                else:
                    result = do_error(XSubmission.create_from_xobject(xobject), "Unknown method for scilab-server: %s" % method)

                xsession.put_xresult(result)
                logger.info("put_xresult completed")

            # decrease length size
            length -= 1

        elif not length_result:

            # In case of error length will contain detailed requests error message
            logger.error(length)

        time.sleep(POLL_INTERVAL)


def do_error(xsubmission, msg=None):
    xsubmission.set_grade(grade=0, feedback=msg, correctness=False, success=False)
    return xsubmission


if __name__ == "__main__":
    main()
