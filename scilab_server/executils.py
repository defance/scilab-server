# -*- coding=utf-8 -*-

import fcntl
import os
import logging


logger = logging.getLogger(__name__)


def demote(user_uid=os.geteuid(), user_gid=os.getegid()):
    """
    Устанавливаем пользователя и группу, необходимо для инициализации
    дочернего процесса.

    :param user_uid: Пользователь
    :param user_gid: Группа
    :return: Инициализирующая функция
    """
    def result():
        os.seteuid(user_uid)
        os.setegid(user_gid)
        os.setpgrp()
    return result


def read_all(process):
    """
    Читает stdout из процесса. Он должен быть запущен в неблокирующем
    режиме вывода.

    См. http://eyalarubas.com/python-subproc-nonblock.html

    :param process: Процесс
    :return: Вывод процесса
    """
    result = ''
    file_desc = process.stdout.fileno()
    while True:
        try:
            data = os.read(file_desc, 1024)
            if data == '':
                break
            result += data
        except OSError:
            break
    return result


def set_non_block(process):
    """
    Устанавилвает stdout в неблокирующий режим.

    См. http://eyalarubas.com/python-subproc-nonblock.html

    :param process: Процесс
    :return:
    """
    try:
        flags = fcntl.fcntl(process.stdout, fcntl.F_GETFL)
        fcntl.fcntl(process.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    except IOError:
        logger.warning("Failed to update process flags: I/O")
