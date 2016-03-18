# -*- coding=utf-8 -*-

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from cgi import FieldStorage
from cStringIO import StringIO
import sys
import logging
import zipfile
import time
import requests
import base64
import tempfile

from scilab_server.executable import spawn_scilab
from scilab_server.settings import *
from xqueue.xgeneration import XGeneration
from xqueue_api import XQueueSession
from xqueue_api.xsubmission import XSubmission

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


def cleanup(cwd):
    cwd.rmtree_p()


def make_result(msg=None, grade=0.0):
    return {
        'msg': msg,
        'grade': grade,
    }


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

    # Полный рабочий путь в системе, со временной директорией, сразу вычистим
    # TODO: generate RANDOM path using guid
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

    generate_code = spawn_scilab(filename, timeout=15)

    try:
        with open(full_path + '/pregenerated', 'r') as f:
            pregenerated = f.read()
    except IOError:
        return xgeneration.set_generation_result(False, "Pregenerated read error")

    xgeneration.set_generation_result(True, pregenerated)

    return xgeneration


def do_check(xsubmission):

    xsubmission.set_grade(grader='scilab_grader_01')

    result = {}

    # Dicts
    student_input = json.loads(xsubmission.student_response)
    grader_payload = xsubmission.grader_payload

    # Archives
    data = get_archives(student_input.get('archive_64_url'))

    student_filename, student_file = get_raw_archive(data, 'user_archive')
    instructor_filename, instructor_file = get_raw_archive(data, 'instructor_archive')

    # Проверка на то, что это действительно zip
    if student_filename.ext != '.zip':
        return xsubmission.set_grade(feedback='NZ: Загруженный файл должен быть .zip.')

    # Полный рабочий путь в системе, со временной директорией, сразу вычистим
    full_path = tempfile.mkdtemp(prefix=TMP_PATH)

    # Подчистка с самого начала нам не нужна, поскольку можно положиться на то,
    # что будет создан уникальный путь
    # cleanup(cwd=full_path)

    # Получаем архивы
    student_archive = zipfile.ZipFile(student_file)
    instructor_archive = zipfile.ZipFile(instructor_file)

    # Извлекаем архив студента
    try:
        student_archive.extractall(full_path)
    except Exception:
        return xsubmission.set_grade(feedback='SAE: Не удалось открыть архив с ответом.')

    # Процессу разрешено выполняться только 2 секунды
    filename = full_path / SCILAB_STUDENT_SCRIPT

    # Допишем функцию выходна, на всякий случай
    with open(filename, "a") as source_file:
        source_file.write("exit();")

    student_code = spawn_scilab(filename, timeout=15)
    if student_code.get('return_code') == -1:
        return xsubmission.set_grade(feedback='TL: Превышен лимит времени')

    # Запишем pregenerated, если он вообще есть
    if xsubmission.grader_payload is not None:
        with open(full_path / "pregenerated", "w") as f:
            f.write(xsubmission.grader_payload)

    try:
        instructor_archive.extractall(full_path)
    except Exception:
        return xsubmission.set_grade(feedback='IAE: Не удалось открыть архив инструктора.')

    filename = full_path / SCILAB_INSTRUCTOR_SCRIPT

    # Допишем функцию выхода, на всякий случай
    with open(filename, "a") as source_file:
        source_file.write("\nexit();\n")

    checker_code = spawn_scilab(filename, timeout=15)
    if checker_code.get('return_code') == -1:
        return xsubmission.set_grade(feedback='ITL: Превышен лимит времени инструктором')

    try:
        f = open(full_path / 'check_output')
        result_grade = float(f.readline().strip())
        result_message = f.readline().strip()
    except IOError:
        return xsubmission.set_grade(feedback='COE: Не удалось определить результат проверки.')

    return xsubmission.set_grade(grade=result_grade, feedback=result_message, correctness=True)


def main():

    # Начинаем работу сервера
    print ("Start polling xqueue")
    print ("xqueue url = %s" % XQUEUE_INTERFACE['url'])
    while True:
        xsession = XQueueSession(base_url=XQUEUE_INTERFACE['url'],
                                 username=XQUEUE_INTERFACE['login'],
                                 password=XQUEUE_INTERFACE['password'],
                                 queue=XQUEUE_INTERFACE['queue'],
                                 autoconnect=True)
        length_result, length = xsession.get_len()
        if length_result and length:

            print "Non zero length, retrieve submission"

            xobject_result, xobject = xsession.get_xobject()
            if xobject_result:

                body = json.loads(xobject.body)
                method = body['method']

                # print u">%s<" % method
                # print u"method==check => %s" % (method == u'check')
                # print u"method==generate => %s" % (method == u'generate')
                # print u"method==generate => %s" % (method == u'generate')

                if method == u'check':
                    result = do_check(XSubmission.create_from_xobject(xobject))

                elif method == u'generate':
                    print u"method==generate => %s" % (method == u'generate')
                    result = do_generate(XGeneration.create_from_xobject(xobject))

                else:
                    print u"unknown method: %s" % method
                    print u"method==check => %s" % (method == u'check')
                    print u"method==generate => %s" % (method == u'generate')
                    result = make_result("Unknown method: %s" % method)

                xsession.put_xresult(result)

            # decrease length size
            length -= 1

        print "Will now sleep %ss" % POLL_INTERVAL
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
