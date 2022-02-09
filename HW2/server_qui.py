import sys
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QLabel, QTableView, QDialog, QPushButton, \
    QLineEdit, QFileDialog, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt
import os


# GUI - Создание таблицы QModel, для отображения в окне программы.
def gui_create_model(database):
    list_users = database.active_users_list()
    list_table = QStandardItemModel()
    list_table.setHorizontalHeaderLabels(['Имя Клиента', 'IP Адрес', 'Порт', 'Время подключения'])
    for row in list_users:
        user, ip, port, time = row
        user = QStandardItem(user)
        user.setEditable(False)
        ip = QStandardItem(ip)
        ip.setEditable(False)
        port = QStandardItem(str(port))
        port.setEditable(False)
        # Уберём миллисекунды из строки времени, т.к. такая точность не требуется.
        time = QStandardItem(str(time.replace(microsecond=0)))
        time.setEditable(False)
        list_table.appendRow([user, ip, port, time])
    return list_table


# GUI - Функция реализующая заполнение таблицы историей сообщений.
def create_stat_model(database):
    # Список записей из базы
    hist_list = database.message_history()

    # Объект модели данных:
    list_table = QStandardItemModel()
    list_table.setHorizontalHeaderLabels(
        ['Имя Клиента', 'Последний раз входил', 'Сообщений отправлено', 'Сообщений получено'])
    for row in hist_list:
        user, last_seen, sent, recvd = row
        user = QStandardItem(user)
        user.setEditable(False)
        last_seen = QStandardItem(str(last_seen.replace(microsecond=0)))
        last_seen.setEditable(False)
        sent = QStandardItem(str(sent))
        sent.setEditable(False)
        recvd = QStandardItem(str(recvd))
        recvd.setEditable(False)
        list_table.appendRow([user, last_seen, sent, recvd])
    return list_table


# Класс основного окна
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Кнопка выхода
        exitAction = QAction('Выход', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(qApp.quit)

        # Кнопка обновить список клиентов
        self.refresh_button = QAction('Обновить список', self)

        # Кнопка настроек сервера
        self.config_btn = QAction('Настройки сервера', self)

        # Кнопка вывести историю сообщений
        self.show_history_button = QAction('История клиентов', self)

        # Статусбар
        # dock widget
        self.statusBar()

        # Тулбар
        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(exitAction)
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_history_button)
        self.toolbar.addAction(self.config_btn)

        # Настройки геометрии основного окна
        # Поскольку работать с динамическими размерами мы не умеем, и мало времени на изучение, размер окна фиксирован.
        self.setFixedSize(800, 600)
        self.setWindowTitle('Messaging Server alpha release')

        # Надпись о том, что ниже список подключённых клиентов
        self.label = QLabel('Список подключённых клиентов:', self)
        self.label.setFixedSize(240, 15)
        self.label.move(10, 25)

        # Окно со списком подключённых клиентов.
        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 45)
        self.active_clients_table.setFixedSize(780, 400)

        # Последним параметром отображаем окно.
        self.show()


# Класс окна с историей пользователей
class HistoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Настройки окна:
        self.setWindowTitle('Статистика клиентов')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Кнопка закрытия окна
        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(250, 650)
        self.close_button.clicked.connect(self.close)

        # Лист с собственно историей
        self.history_table = QTableView(self)
        self.history_table.move(10, 10)
        self.history_table.setFixedSize(580, 620)

        self.show()


# Класс окна настроек
class ConfigWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        """
        Общий предок для клиента и сервера.
        """
        import socket
        from abc import ABC, abstractmethod
        from message import Message
        import logging
        import time
        from common.variables import *
        from descrptrs import Port
        from metaclasses import ServerVerifier, TransportVerifier
        from errors import ServerError

        # class Transport(ABC):
        class Transport(metaclass=TransportVerifier):
            """
            Класс определеят общие свойства и методы для клиента и сервера.
            """
            LOGGER = logging.getLogger('')  # инициализируем атрибут класса
            # Валидация значения порта через дескриптор
            port = Port()

            # # Валидация значения порта через метод __new__ (рабочий код)
            # def __new__(cls, *args, **kwargs):
            #     try:
            #         port = int(args[1])
            #         if port < 1024 or port > 65535:
            #             raise ValueError
            #     except ValueError:
            #         cls.LOGGER.critical(
            #             f'Попытка запуска клиента с неподходящим номером порта: {port}.'
            #             f' Допустимы адреса с 1024 до 65535')
            #         return -1
            #     except IndexError:
            #         cls.LOGGER.critical('Не указан номер порта.')
            #         return -1
            #     #  если значения параметров корреткны создаем объект
            #     return super().__new__(cls)

            def __init__(self, ipaddress, port):
                self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.ipaddress = ipaddress
                self.port = int(port)
                self.LOGGER.info(f'Создан объект типа {type(self)}, присвоен сокет {self.socket}')

            # Сокет для обмена сообщениями
            @property
            def socket(self):
                """ Получаем сокет"""
                return self.__socket

            # Инициализация сервера/клента
            # @abstractmethod
            def init(self):
                pass

            # Запуск сервера/клиента
            # @abstractmethod
            def run(self):
                pass

            # Обработать сообщение (послать или получить в зависимости от типа транспорта)
            # @abstractmethod
            def process_message(self, message):
                pass

            # Послать сообщение адресвту
            @staticmethod
            def send(tosocket, message):
                Message.send(tosocket, message)

            # Принять сообщение от адресвта
            @staticmethod
            def get(fromsocket):
                return Message.get(fromsocket)

            # Возвращает рабочий набор ip-адреса и порта
            @property
            def connectstring(self):
                return (self.ipaddress, self.port)

            # Устнавливаеи тип логгера в зависимости от функции (клиент или сервер)
            @classmethod
            def set_logger_type(cls, logtype):
                cls.LOGGER = logging.getLogger(logtype)
                return cls.LOGGER

            @staticmethod
            def create_exit_message(account_name):
                """Функция создаёт словарь с сообщением о выходе"""
                return {
                    ACTION: EXIT,
                    TIME: time.time(),
                    ACCOUNT_NAME: account_name
                }

            @staticmethod
            def print_help():
                """Функция выводящяя справку по использованию"""
                print('Поддерживаемые команды:')
                print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
                print('help - вывести подсказки по командам')
                print('exit - выход из программы')

            @staticmethod
            # Функция запроса списка известных пользователей
            def user_list_request(sock, username):
                Transport.LOGGER.debug(f'Запрос списка известных пользователей {username}')
                req = {
                    ACTION: USERS_REQUEST,
                    TIME: time.time(),
                    ACCOUNT_NAME: username
                }
                Transport.send(sock, req)
                ans = Transport.get(sock)
                if RESPONSE in ans and ans[RESPONSE] == 202:
                    return ans[LIST_INFO]
                else:
                    raise ServerError

            @staticmethod
            # Функция запрос контакт листа
            def contacts_list_request(sock, name):
                Transport.LOGGER.debug(f'Запрос контакт листа для пользователя {name}')
                req = {
                    ACTION: GET_CONTACTS,
                    TIME: time.time(),
                    USER: name
                }
                Transport.LOGGER.debug(f'Сформирован запрос {req}')
                Transport.send(sock, req)
                ans = Transport.get(sock)
                Transport.LOGGER.debug(f'Получен ответ {ans}')
                if RESPONSE in ans and ans[RESPONSE] == 202:
                    return ans[LIST_INFO]
                else:
                    raise ServerError

            @staticmethod
            # Функция добавления пользователя в контакт лист
            def add_contact(sock, username, contact):
                Transport.LOGGER.debug(f'Создание контакта {contact}')
                req = {
                    ACTION: ADD_CONTACT,
                    TIME: time.time(),
                    USER: username,
                    ACCOUNT_NAME: contact
                }
                Transport.send(sock, req)
                ans = Transport.get(sock)
                if RESPONSE in ans and ans[RESPONSE] == 200:
                    pass
                else:
                    raise ServerError('Ошибка создания контакта')
                print('Удачное создание контакта.')

            @staticmethod
            # Функция удаления пользователя из контакт листа
            def remove_contact(sock, username, contact):
                Transport.LOGGER.debug(f'Создание контакта {contact}')
                req = {
                    ACTION: REMOVE_CONTACT,
                    TIME: time.time(),
                    USER: username,
                    ACCOUNT_NAME: contact
                }
                Transport.send(sock, req)
                ans = Transport.get(sock)
                if RESPONSE in ans and ans[RESPONSE] == 200:
                    pass
                else:
                    raise ServerError('Ошибка удаления клиента')
                print('Удачное удаление')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.statusBar().showMessage('Test Statusbar Message')
    test_list = QStandardItemModel(main_window)
    test_list.setHorizontalHeaderLabels(['Имя Клиента', 'IP Адрес', 'Порт', 'Время подключения'])
    test_list.appendRow(
        [QStandardItem('test1'), QStandardItem('192.198.0.5'), QStandardItem('23544'), QStandardItem('16:20:34')])
    test_list.appendRow(
        [QStandardItem('test2'), QStandardItem('192.198.0.8'), QStandardItem('33245'), QStandardItem('16:22:11')])
    main_window.active_clients_table.setModel(test_list)
    main_window.active_clients_table.resizeColumnsToContents()
    app.exec_()

    # ----------------------------------------------------------
    # app = QApplication(sys.argv)
    # dial = ConfigWindow()
    #
    # app.exec_()

    # ----------------------------------------------------------
    # app = QApplication(sys.argv)
    # window = HistoryWindow()
    # test_list = QStandardItemModel(window)
    # test_list.setHorizontalHeaderLabels(
    #     ['Имя Клиента', 'Последний раз входил', 'Отправлено', 'Получено'])
    # test_list.appendRow(
    #     [QStandardItem('test1'), QStandardItem('Fri Dec 12 16:20:34 2020'), QStandardItem('2'), QStandardItem('3')])
    # test_list.appendRow(
    #     [QStandardItem('test2'), QStandardItem('Fri Dec 12 16:23:12 2020'), QStandardItem('8'), QStandardItem('5')])
    # window.history_table.setModel(test_list)
    # window.history_table.resizeColumnsToContents()
    #
    # app.exec_()