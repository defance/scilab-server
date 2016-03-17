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


def do_check(xsubmission):
    raise NotImplementedError()


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
    cleanup(cwd=full_path)

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


class ScilabServer(object):

    def do_check(self):

        def do():

            result = {}

            # Dicts
            student_input = json.loads(self.xsubmission.student_response)
            grader_payload = self.xsubmission.grader_payload

            # Archives
            data = get_archives(student_input.get('archive_64_url'))

            student_filename, student_file = get_raw_archive(data, 'user_archive')
            instructor_filename, instructor_file = get_raw_archive(data, 'instructor_archive')

            # Проверка на то, что это действительно zip
            if student_filename.ext != '.zip':
                raise Exception('NZ: Загруженный файл должен быть .zip.')

            # Полный рабочий путь в системе, со временной директорией, сразу вычистим
            full_path = TMP_PATH / student_filename.stripext()
            cleanup(cwd=full_path)

            # Получаем архивы
            student_archive = zipfile.ZipFile(student_file)
            instructor_archive = zipfile.ZipFile(instructor_file)

            # Извлекаем архив студента
            try:
                student_archive.extractall(full_path)
            except Exception:
                return make_result(msg='SAE: Не удалось открыть архив с ответом.')

            # Процессу разрешено выполняться только 2 секунды
            filename = full_path / SCILAB_STUDENT_SCRIPT

            # Допишем функцию выходна, на всякий случай
            with open(filename, "a") as source_file:
                source_file.write("exit();")

            student_code = spawn_scilab(filename, timeout=15)
            if student_code.get('return_code') == -1:
                return make_result(msg='TL: Превышен лимит времени')

            try:
                instructor_archive.extractall(full_path)
            except Exception:
                return make_result(msg='IAE: Не удалось открыть архив инструктора.')

            filename = full_path / SCILAB_INSTRUCTOR_SCRIPT

            # Допишем функцию выхода, на всякий случай
            with open(filename, "a") as source_file:
                source_file.write("\nexit();\n")

            checker_code = spawn_scilab(filename, timeout=15)
            if checker_code.get('return_code') == -1:
                return make_result(msg='ITL: Превышен лимит времени инструктором')

            try:
                f = open(full_path + '/checker_output')
                result_grade = float(f.readline().strip())
                result_message = f.readline().strip()
            except IOError:
                return make_result(
                    msg='COE: Не удалось определить результат проверки.'
                )

            return make_result(msg=result_message, grade=result_grade)

        res = do()
        self.xsubmission.set_grade(grade=res['grade'], feedback=res['msg'], grader='scilab_grader_01', correctness=True)
        return self.xsubmission


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

                if method == u'check':
                    result = do_check(XSubmission.create_from_xobject(xobject))

                elif method == u'generate':
                    result = do_generate(XGeneration.create_from_xobject(xobject))

                else:
                    result = make_result("Unknown method: %s" % method)

                xsession.put_xresult(result)

            # decrease length size
            length -= 1

        print "Will now sleep %ss" % POLL_INTERVAL
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
