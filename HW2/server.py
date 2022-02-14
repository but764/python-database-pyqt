from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from common.variables import *
import datetime


# Класс - серверная база данных:
class ServerStorage:
    # Класс - отображение таблицы всех пользователей
    # Экземпляр этого класса - запись в таблице AllUsers
    class AllUsers:
        def __init__(self, username):
            self.name = username
            self.last_login = datetime.datetime.now()
            self.id = None

    # Класс - отображение таблицы активных пользователей:
    # Экземпляр этого класса - запись в таблице ActiveUsers
    class ActiveUsers:
        def __init__(self, user_id, ip_address, port, login_time):
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time
            self.id = None


    # Класс - отображение таблицы истории входов
    # Экземпляр этого класса - запись в таблице LoginHistory
    class LoginHistory:
        def __init__(self, name, date, ip, port):
            self.id = None
            self.name = name
            self.date_time = date
            self.ip = ip
            self.port = port

    # Класс - отображение таблицы контактов пользователей
    class UsersContacts:
        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    # Класс отображение таблицы истории действий
    class UsersHistory:
        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0



    def __init__(self, path):
        # Создаём движок базы данных
        # ранее было SERVER_DATABASE - sqlite:///server_base.db3
        # echo=False - отключает вывод на экран sql-запросов)
        # pool_recycle - по умолчанию соединение с БД через 8 часов простоя обрывается
        # Чтобы этого не случилось необходимо добавить pool_recycle=7200 (переустановка
        #    соединения через каждые 2 часа)
        self.database_engine = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})

        # Создаём объект MetaData
        self.metadata = MetaData()

        # Создаём таблицу пользователей
        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime)
                            )

        # Создаём таблицу активных пользователей
        active_users_table = Table('Active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('Users.id'), unique=True),
                                   Column('ip_address', String),
                                   Column('port', Integer),
                                   Column('login_time', DateTime)
                                   )

        # Создаём таблицу истории входов
        user_login_history = Table('Login_history', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('name', ForeignKey('Users.id')),
                                   Column('date_time', DateTime),
                                   Column('ip', String),
                                   Column('port', String)
                                   )

        # Создаём таблицу контактов пользователей
        contacts = Table('Contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('user', ForeignKey('Users.id')),
                         Column('contact', ForeignKey('Users.id'))
                         )

        # Создаём таблицу истории пользователей
        users_history_table = Table('History', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('Users.id')),
                                    Column('sent', Integer),
                                    Column('accepted', Integer)
                                    )

        # Создаём таблицы
        self.metadata.create_all(self.database_engine)

        # Создаём отображения
        # Связываем класс в ORM с таблицей
        mapper(self.AllUsers, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.LoginHistory, user_login_history)
        mapper(self.UsersContacts, contacts)
        mapper(self.UsersHistory, users_history_table)

        # Создаём сессию
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Если в таблице активных пользователей есть записи, то их необходимо удалить
        # Когда устанавливаем соединение, очищаем таблицу активных пользователей
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    # Функция выполняющаяся при входе пользователя, записывает в базу факт входа
    def user_login(self, username, ip_address, port):
        #  print(username, ip_address, port)
        # Запрос в таблицу пользователей на наличие там пользователя с таким именем
        rez = self.session.query(self.AllUsers).filter_by(name=username)

        # Если имя пользователя уже присутствует в таблице, обновляем время последнего входа
        if rez.count():
            user = rez.first()
            user.last_login = datetime.datetime.now()
        # Если нет, то создаём нового пользователя
        else:
            # Создаём экземпляр класса self.AllUsers, через который передаём данные в таблицу
            user = self.AllUsers(username)
            self.session.add(user)
            # Комит здесь нужен, чтобы присвоился ID
            self.session.commit()
            self.session.commit()
            user_in_history = self.UsersHistory(user.id)
            self.session.add(user_in_history)

        # Теперь можно создать запись в таблицу активных пользователей о факте входа.
        # Создаём экземпляр класса self.ActiveUsers, через который передаём данные в таблицу
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        # и сохранить в истории входов
        # Создаём экземпляр класса self.LoginHistory, через который передаём данные в таблицу
        history = self.LoginHistory(user.id, datetime.datetime.now(), ip_address, port)
        self.session.add(history)

        # Сохраняем изменения
        self.session.commit()

    # Функция, фиксирующая отключение пользователя
    def user_logout(self, username):
        # Запрашиваем пользователя, что покидает нас
        # получаем запись из таблицы self.AllUsers
        user = self.session.query(self.AllUsers).filter_by(name=username).first()

        # Удаляем его из таблицы активных пользователей.
        # Удаляем запись из таблицы self.ActiveUsers
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()

        # Применяем изменения
        self.session.commit()


    # Функция фиксирует передачу сообщения и делает соответствующие отметки в БД
    def process_message(self, sender, recipient):
        # Получаем ID отправителя и получателя
        sender = self.session.query(self.AllUsers).filter_by(name=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(name=recipient).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(self.UsersHistory).filter_by(user=sender).first()
        sender_row.sent += 1
        recipient_row = self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        recipient_row.accepted += 1

        self.session.commit()


    # Функция добавляет контакт для пользователя.
    def add_contact(self, user, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что не дубль и что контакт может существовать (полю пользователь мы доверяем)
        if not contact or self.session.query(self.UsersContacts).filter_by(user=user.id, contact=contact.id).count():
            return

        # Создаём объект и заносим его в базу
        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()


    # Функция удаляет контакт из базы данных
    def remove_contact(self, user, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что контакт может существовать (полю пользователь мы доверяем)
        if not contact:
            return

        # Удаляем требуемое
        print(self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id
        ).delete())
        self.session.commit()


    # Функция возвращает список известных пользователей со временем последнего входа.
    def users_list(self):
        # Запрос строк таблицы пользователей.
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login
        )
        # Возвращаем список кортежей
        return query.all()

    # Функция возвращает список активных пользователей
    def active_users_list(self):
        # Запрашиваем соединение таблиц и собираем кортежи имя, адрес, порт, время.
        query = self.session.query(
            self.AllUsers.name,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()

    # Функция, возвращающая историю входов по пользователю или всем пользователям
    def login_history(self, username=None):
        # Запрашиваем историю входа
        query = self.session.query(self.AllUsers.name,
                                   self.LoginHistory.date_time,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        # Если было указано имя пользователя, то фильтруем по этому имени
        if username:
            query = query.filter(self.AllUsers.name == username)
        # Возвращаем список кортежей
        return query.all()

    # Функция возвращает список контактов пользователя.
    def get_contacts(self, username):
        # Запрашиваем указанного пользователя
        user = self.session.query(self.AllUsers).filter_by(name=username).one()

        # Запрашиваем его список контактов
        query = self.session.query(self.UsersContacts, self.AllUsers.name). \
            filter_by(user=user.id). \
            join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)

        # выбираем только имена пользователей и возвращаем их.
        return [contact[1] for contact in query.all()]

    # Функция возвращает количество переданных и полученных сообщений
    def message_history(self):
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()



# Отладка
if __name__ == '__main__':
    """Программа-сервер"""

    import sys
    import os
    import argparse
    import select
    import logs.config_server_log
    from common.variables import *
    from transport import Transport
    from common.decorators import log, logc
    from metaclasses import ServerVerifier
    from server_database import ServerStorage
    import threading
    import configparser  # https://docs.python.org/3/library/configparser.html
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import QTimer
    from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow
    from PyQt5.QtGui import QStandardItemModel, QStandardItem

    # Флаг, что был подключён новый пользователь, нужен чтобы не мучать BD
    # постоянными запросами на обновление
    new_connection = False
    conflag_lock = threading.Lock()


    class Server(threading.Thread, Transport, metaclass=ServerVerifier):
        """
        Класс определеят свойства и методы для сервера
        """

        def __init__(self, ipaddress, port, database):
            self.LOGGER = Transport.set_logger_type('server')
            Transport.__init__(self, ipaddress, port)
            # База данных сервера
            self.database = database
            # Конструктор предка
            threading.Thread.__init__(self)

            self.LOGGER.info(f'Сервер подключаем по адресу {ipaddress} на порту {port}')

        @logc
        def init(self):
            self.socket.bind(self.connectstring)
            self.socket.settimeout(0.5)
            # Слушаем порт
            self.socket.listen(MAX_CONNECTIONS)
            self.LOGGER.info('Сервер начал слушать порт')
            self.clients = []
            self.messages = []
            # Словарь, содержащий имена пользователей и соответствующие им сокеты.
            self.names = dict()

        # Обработчик сообщений от клиентов, принимает словарь: сообщение от клиента,
        # проверяет: корректность,
        # отправляет: словарь-ответ в случае необходимости.
        @logc
        def process_client_message(self, message, message_list, client):
            global new_connection
            self.LOGGER.debug(f'Разбор сообщения от клиента : {message}')

            # Если это сообщение о присутствии, принимаем и отвечаем
            if ACTION in message and message[ACTION] == PRESENCE and \
                    TIME in message and USER in message:
                # Если такой пользователь ещё не зарегистрирован,
                # регистрируем, иначе отправляем ответ и завершаем соединение.
                if message[USER][ACCOUNT_NAME] not in self.names.keys():
                    self.names[message[USER][ACCOUNT_NAME]] = client
                    client_ip, client_port = client.getpeername()
                    self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                    self.send(client, RESPONSE_200)
                    with conflag_lock:
                        new_connection = True
                else:
                    response = RESPONSE_400
                    response[ERROR] = 'Имя пользователя уже занято.'
                    self.send(client, response)
                    self.clients.remove(client)
                    client.close()
                return

            # Если это сообщение, то добавляем его в очередь сообщений. Ответ не требуется.
            elif ACTION in message and message[ACTION] == MESSAGE and \
                    DESTINATION in message and TIME in message \
                    and SENDER in message and MESSAGE_TEXT in message \
                    and self.names[message[SENDER]] == client:
                if message[DESTINATION] in self.names:
                    self.messages.append(message)
                    self.database.process_message(message[SENDER], message[DESTINATION])
                    self.send(client, RESPONSE_200)
                else:
                    response = RESPONSE_400
                    response[ERROR] = 'Пользователь не зарегистрирован на сервере.'
                    self.send(client, response)
                return

            # Если клиент выходит
            elif ACTION in message and message[ACTION] == EXIT \
                    and ACCOUNT_NAME in message \
                    and self.names[message[ACCOUNT_NAME]] == client:
                self.LOGGER.info(f'Клиент {message[ACCOUNT_NAME]} корректно отключился от сервера.')
                self.database.user_logout(message[ACCOUNT_NAME])
                self.clients.remove(self.names[message[ACCOUNT_NAME]])
                self.names[message[ACCOUNT_NAME]].close()
                del self.names[message[ACCOUNT_NAME]]
                with conflag_lock:
                    new_connection = True
                return

            # Если это запрос контакт-листа
            elif ACTION in message and message[ACTION] == GET_CONTACTS and USER in message and \
                    self.names[message[USER]] == client:
                response = RESPONSE_202
                response[LIST_INFO] = self.database.get_contacts(message[USER])
                self.send(client, response)

            # Если это добавление контакта
            elif ACTION in message and message[ACTION] == ADD_CONTACT and ACCOUNT_NAME in message and USER in message \
                    and self.names[message[USER]] == client:
                self.database.add_contact(message[USER], message[ACCOUNT_NAME])
                self.send(client, RESPONSE_200)

            # Если это удаление контакта
            elif ACTION in message and message[ACTION] == REMOVE_CONTACT and ACCOUNT_NAME in message and USER in message \
                    and self.names[message[USER]] == client:
                self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
                self.send(client, RESPONSE_200)

            # Если это запрос известных пользователей
            elif ACTION in message and message[ACTION] == USERS_REQUEST and ACCOUNT_NAME in message \
                    and self.names[message[ACCOUNT_NAME]] == client:
                response = RESPONSE_202
                response[LIST_INFO] = [user[0]
                                       for user in self.database.users_list()]
                self.send(client, response)

            # Иначе отдаём Bad request
            else:
                response = RESPONSE_400
                response[ERROR] = 'Запрос некорректен.'
                self.send(client, response)
                return

        # Функция адресной отправки сообщения определённому клиенту. Принимает словарь:
        # сообщение, список зарегистрированых пользователей и слушающие сокеты. Ничего не возвращает.
        @logc
        def process_message(self, message, listen_socks):
            if message[DESTINATION] in self.names \
                    and self.names[message[DESTINATION]] in listen_socks:
                self.send(self.names[message[DESTINATION]], message)
                self.LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                                 f'от пользователя {message[SENDER]}.')
            elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
                raise ConnectionError
            else:
                self.LOGGER.error(
                    f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
                    f'отправка сообщения невозможна.')

        @logc
        def run(self):
            """
            Обработчик событий от клиента
            :return:
            """
            while True:
                # Ждём подключения, если таймаут вышел, ловим исключение.
                try:
                    client, client_address = self.socket.accept()
                except OSError:
                    pass
                else:
                    self.LOGGER.info(f'Установлено соедение с ПК {client_address}')
                    # Добавляем клиента в список в конец
                    self.clients.append(client)

                recv_data_lst = []
                send_data_lst = []
                err_lst = []
                # Проверяем на наличие ждущих клиентов
                try:
                    if self.clients:
                        recv_data_lst, send_data_lst, err_lst = select.select(self.clients, self.clients, [], 0)
                except OSError:
                    pass

                # принимаем сообщения и если там есть сообщения,
                # кладём в словарь, если ошибка, исключаем клиента.
                if recv_data_lst:
                    for client_with_message in recv_data_lst:
                        try:
                            self.process_client_message(self.get(client_with_message),
                                                        self.messages, client_with_message)
                        except OSError:
                            # Ищем клиента в словаре клиентов и удаляем его из него
                            # и базы подключённых
                            self.LOGGER.info(f'Клиент {client_with_message.getpeername()} '
                                             f'отключился от сервера.')
                            for name in self.names:
                                if self.names[name] == client_with_message:
                                    self.database.user_logout(name)
                                    del self.names[name]
                                    break
                            self.clients.remove(client_with_message)
                            with conflag_lock:
                                new_connection = True

                # Если есть сообщения для отправки и ожидающие клиенты, отправляем им сообщение.
                for i in self.messages:
                    try:
                        self.process_message(i, send_data_lst)
                    except Exception:
                        self.LOGGER.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                        self.clients.remove(self.names[i[DESTINATION]])
                        self.database.user_logout(i[DESTINATION])
                        del self.names[i[DESTINATION]]
                self.messages.clear()

        @staticmethod
        @log
        def arg_parser(default_port, default_address):
            """Парсер аргументов коммандной строки"""
            parser = argparse.ArgumentParser()
            parser.add_argument('-p', default=default_port, type=int, nargs='?')
            parser.add_argument('-a', default=default_address, nargs='?')
            namespace = parser.parse_args(sys.argv[1:])
            listen_address = namespace.a
            listen_port = namespace.p

            return listen_address, listen_port


    def print_help():
        print('Поддерживаемые комманды:')
        print('users - список известных пользователей')
        print('connected - список подключённых пользователей')
        print('loghist - история входов пользователя')
        print('exit - завершение работы сервера.')
        print('help - вывод справки по поддерживаемым командам')


    # Загрузка файла конфигурации
    def config_load():
        config = configparser.ConfigParser()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        config.read(f"{dir_path}/{'server+++.ini'}")
        # Если конфиг файл загружен правильно, запускаемся, иначе конфиг по умолчанию.
        if 'SETTINGS' in config:
            return config
        else:
            config.add_section('SETTINGS')
            config.set('SETTINGS', 'Default_port', str(DEFAULT_PORT))
            config.set('SETTINGS', 'Listen_Address', '')
            config.set('SETTINGS', 'Database_path', '')
            config.set('SETTINGS', 'Database_file', 'server_database.db3')
            return config


    def main():
        # Загрузка файла конфигурации сервера
        config = config_load()

        dir_path = os.path.dirname(os.path.realpath(__file__))
        config.read(f"{dir_path}/{'server.ini'}")

        # Загрузка параметров командной строки, если нет параметров, то задаём
        # значения по умоланию.
        # listen_address, listen_port = Server.arg_parser()
        listen_address, listen_port = Server.arg_parser(
            config['SETTINGS']['Default_port'], config['SETTINGS']['Listen_Address'])

        # Инициализация базы данных
        database = ServerStorage(
            os.path.join(
                config['SETTINGS']['Database_path'],
                config['SETTINGS']['Database_file']))

        # Создание экземпляра класса - сервера и его запуск:
        srv = Server(listen_address, listen_port, database)
        # Если не прошли проверку на ValueError выходим из программы
        if srv == -1:
            sys.exit(1)
        # Инициализируем листенер
        srv.init()

        srv.daemon = True
        srv.start()

        # # Начинаем принимать сообщения
        # srv.run()
        #

        # Создаём графическое окружение для сервера:
        server_app = QApplication(sys.argv)
        main_window = MainWindow()

        # Инициализируем параметры в окна
        main_window.statusBar().showMessage('Server Working')
        main_window.active_clients_table.setModel(gui_create_model(database))
        main_window.active_clients_table.resizeColumnsToContents()
        main_window.active_clients_table.resizeRowsToContents()

        # Функция, обновляющая список подключённых, проверяет флаг подключения, и
        # если надо обновляет список
        def list_update():
            global new_connection
            if new_connection:
                main_window.active_clients_table.setModel(
                    gui_create_model(database))
                main_window.active_clients_table.resizeColumnsToContents()
                main_window.active_clients_table.resizeRowsToContents()
                with conflag_lock:
                    new_connection = False

        # Функция, создающая окно со статистикой клиентов
        def show_statistics():
            global stat_window
            stat_window = HistoryWindow()
            stat_window.history_table.setModel(create_stat_model(database))
            stat_window.history_table.resizeColumnsToContents()
            stat_window.history_table.resizeRowsToContents()
            stat_window.show()

        # Функция создающяя окно с настройками сервера.
        def server_config():
            global config_window
            # Создаём окно и заносим в него текущие параметры
            config_window = ConfigWindow()
            config_window.db_path.insert(config['SETTINGS']['Database_path'])
            config_window.db_file.insert(config['SETTINGS']['Database_file'])
            config_window.port.insert(config['SETTINGS']['Default_port'])
            config_window.ip.insert(config['SETTINGS']['Listen_Address'])
            config_window.save_btn.clicked.connect(save_server_config)

        # Функция сохранения настроек
        def save_server_config():
            global config_window
            message = QMessageBox()
            config['SETTINGS']['Database_path'] = config_window.db_path.text()
            config['SETTINGS']['Database_file'] = config_window.db_file.text()
            try:
                port = int(config_window.port.text())
            except ValueError:
                message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
            else:
                config['SETTINGS']['Listen_Address'] = config_window.ip.text()
                if 1023 < port < 65536:
                    config['SETTINGS']['Default_port'] = str(port)
                    print(port)
                    with open('server.ini', 'w') as conf:
                        config.write(conf)
                        message.information(
                            config_window, 'OK', 'Настройки успешно сохранены!')
                else:
                    message.warning(
                        config_window,
                        'Ошибка',
                        'Порт должен быть от 1024 до 65536')

        # Таймер, обновляющий список клиентов 1 раз в секунду
        timer = QTimer()
        timer.timeout.connect(list_update)
        timer.start(1000)

        # Связываем кнопки с процедурами
        main_window.refresh_button.triggered.connect(list_update)
        main_window.show_history_button.triggered.connect(show_statistics)
        main_window.config_btn.triggered.connect(server_config)

        # Запускаем GUI
        server_app.exec_()

        #
        # # Печатаем справку:
        # print_help()
        #
        # # Основной цикл сервера:
        # while True:
        #     command = input('Введите команду: ')
        #     if command == 'help':
        #         print_help()
        #     elif command == 'exit':
        #         break
        #     elif command == 'users':
        #         for user in sorted(database.users_list()):
        #             print(f'Пользователь {user[0]}, последний вход: {user[1]}')
        #     elif command == 'connected':
        #         for user in sorted(database.active_users_list()):
        #             print(f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
        #     elif command == 'loghist':
        #         name = input('Введите имя пользователя для просмотра истории. '
        #                      'Для вывода всей истории, просто нажмите Enter: ')
        #         for user in sorted(database.login_history(name)):
        #             print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
        #     else:
        #         print('Команда не распознана.')


    if __name__ == '__main__':
        main()