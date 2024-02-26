# -*- coding: utf8 -*-
import telebot
from telebot import types
from telebot.types import  InputFile
import requests
import os
from openpyxl import load_workbook
import datetime
import sqlite3
import re
import random
import gspread
from gspread import Client, Spreadsheet, Worksheet
from datetime import datetime, timedelta, timezone
from loguru import logger
from flask import Flask, request

API_TOKEN = '7000908905:AAFIQskVbiFhiBuTsyTO-mVpdwDeRUfQ0Bc'
WEBHOOK_HOST = 'https://etedsfeqa.ru'
WEBHOOK_PORT = 443  # По умолчанию для HTTPS-подключений используется порт 443
WEBHOOK_LISTEN = '0.0.0.0'  # Слушаем все входящие запросы

app = Flask(__name__)
bot = telebot.TeleBot(API_TOKEN)





#ПУТИ К ФАЙЛАМ !!!!!!!!!!!!!!!!!!!!!!

gc: Client = gspread.service_account("../bottelegram/service-account.json") #json файл аккаунта
DataBaseFile = '../bottelegram/use.db' #путь к бд
#путь к примеру (фото) 749 строка
user_location = None
wb = ''

def custom_time_formatter(record):
    record_time = datetime.utcnow() + timedelta(hours=3)
    record["time"] = record_time
    return "{time} {level} {message}\n".format(**record)

# Настройка логирования с ротацией каждый день в полночь и сжатием в архив
logger.add("../bottelegram/debug/debug.log", format=custom_time_formatter, level="DEBUG", rotation="00:00")

userurl = ''

mem_list = ['еблан? ссылку дай..','лан, не урчи', 'бля ну ты и ...', 'ебланчик завали уже пж🤓', 'закибербулить тебя?', 'клоун ты ', 'нет ты', 'чоп чоп чоп', 'я твою маму знаю', 'не еби мои 1 и 0', 'блять просто дай мне нормальную ссылку..', 'боже чел, как зарядки поживают!!??', 'я научусь жаловаться @kravchenko_0013']
# Обработчик команды /start или нажатия на кнопку "начать"
@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f" {message.from_user.username} handler comm = start ")
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('Настройки', 'Сделать вещи')
    bot.send_message(message.chat.id, "Привет! Выберите действие:", reply_markup=markup)



@bot.message_handler(commands=['spamv'])
#спам вики
def spam_puffsun(message):
    i = 0
    if message.chat.id == 5045737709 or message.chat.id == 875402165:
        logger.info(f" {message.from_user.username} handler comm = spam ")
        while i <= 10:
            bot.send_message("2097463384", "Где 200р?")
            logger.info(f" {message.from_user.username} handler comm = spam {i} ")
            i += 1


# Обработчик нажатия на кнопку "Настройки"
@bot.message_handler(func=lambda message: message.text == 'Настройки')
def change_location(message):
    logger.info(f" {message.from_user.username} handler comm = change_location")
    #получение локации уже установленной
    conn = sqlite3.connect(DataBaseFile)
    cursor = conn.cursor()
    people_id = message.chat.id
    cursor.execute(f"SELECT id FROM info WHERE id = {people_id}")
    data = cursor.fetchone()
    if data is None:
        bot.send_message(message.chat.id, "У вас еще не установленна локация, введите название")
        bot.register_next_step_handler(message, save_location)
    else:
        cursor.execute(f"SELECT locatename FROM info WHERE id = {people_id}")
        user_location = cursor.fetchone()[0]
        markup2 = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup2.row('Изменить локацию','Назад')
        bot.send_message(message.chat.id, f"Ваша локация - {user_location}", reply_markup=markup2)

@bot.message_handler(func=lambda message: message.text == 'Изменить локацию')
def change_location(message):
    bot.send_message(message.chat.id, "Введите свою локацию:")
    bot.register_next_step_handler(message, save_location)

# Функция для сохранения локации пользователя
def save_location(message):
    user_location = message.text
    conn = sqlite3.connect(DataBaseFile)

    # Создание объекта-курсора для выполнения SQL-запросов
    cursor = conn.cursor()
    people_id = message.chat.id
    cursor.execute(f"SELECT id FROM info WHERE id = {people_id}")
    data = cursor.fetchone()
    print(data)

    if data is None:
    # add values in fields
        user_id = [message.chat.id]
        cursor.execute("INSERT INTO info (id) VALUES(?);", user_id)


    # Обновление записи в базе данных
    update_query = "UPDATE info SET locatename = ? WHERE id = ?"
    cursor.execute(update_query, (user_location, people_id))
    conn.commit()
    bot.send_message(message.chat.id, "Локация успешно изменена!", reply_markup=create_keyboard())

# Обработчик нажатия на кнопку "Сделать вещи"
@bot.message_handler(func=lambda message: message.text == 'Сделать вещи')
def do_things(message):
    bot.send_message(message.chat.id, "Пришли мне ссылку на таблицу рекордсменов:")
    logger.info(f" {message.from_user.username} handler comm = do_things - сделать вещи нажата")

# Обработчик нажатия на кнопку "Назад"
@bot.message_handler(func=lambda message: message.text == 'Назад')
def do_things(message):
    bot.send_message(message.chat.id, "Изменения сохранены.", reply_markup=create_keyboard())
    logger.info(f" {message.from_user.username} handler comm = do_things - назад нажата")

# Обработчик документа (таблицы рекордсменов)
@bot.message_handler(content_types=['text'])
@logger.catch
def handle_document(message):
    # Диапозоны для ошибок - пустые строки - количества повторений
    range_error_colum = []
    # Определяем диапазоны для перекраски ranges_to_color = ["C4:H4", "C5:H5", "C14:H14"]
    ranges_to_color = []
    # Список значений переменной i в которых находиться разделяющая линия (черные ячейки)
    list_row_fixed = []
    logger.info(f" {message.from_user.username} do_things - поймал текст (как ссылку)")
    userurl = message.text
    regex_patterns = r'((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*'
    result = re.search(regex_patterns, userurl)
    if userurl[:24] != "https://docs.google.com/":
        mem = message.chat.id
        if mem == 5045737709 or mem == 875402165 or mem == 2097463384:
            logger.info(f" {message.from_user.username} do_things - проверка на ссылку НЕ ПРОЙДЕНА (как ссылку)")
            logger.warning(f" {message.from_user.username} id = {message.chat.id} написал в do_things - {userurl} ")
            crack = random.randint(0, 12)
            bot.send_message(message.chat.id, mem_list[crack])
            logger.info(f" {message.from_user.username} ответ бота - {mem_list[crack]}")
    #if not result:
        else:
            logger.info(f" {message.from_user.username} do_things - проверка на ссылку НЕ ПРОЙДЕНА (как ссылку)")
            logger.warning(f" {message.from_user.username} id = {message.chat.id} написал в do_things - {userurl} ")
            bot.send_message(message.chat.id, "Проверьте корректность ссылки.")
    else:

        logger.info(f" {message.from_user.username} do_things - проверка на ссылку ПРОЙДЕНА ")
        logger.info(result.group(0))
        wb = gc.open_by_url(userurl)
        logger.info(f" {message.from_user.username} do_things - подключение к таблице ")

        current_date = datetime.now().strftime('%d.%m.%Y')  # текущая дата
        bot.send_message(message.chat.id, "Начинаю загрузку таблицы...")
        logger.info(f" {message.from_user.username} do_things - сообщение юзеру об начале работы ")

        # Скачивание таблицы Excel
        try:

            bot.send_message(message.chat.id, "Таблица успешно скачана и сохранена")




            # Узнать длину таблицы
            worksheet = wb.get_worksheet(0)
            list_cat_string = worksheet.col_values(2)
            test1 = 0
            i = 1
            while i <= len(list_cat_string):
                if len(list_cat_string[i-1]) == 3:
                    test1 += 1
                i += 1
            print(test1)
            logger.info(f" {message.from_user.username} do_things - длина категорий - {len(list_cat_string)}")
            #len(worksheet.col_values(3))+21
            if test1 <= 4:
                list_of_lists = worksheet.get_all_values()
                row_count = len(list_of_lists)
                range_all = "A1:O"+str(row_count)

                row = "A4:B"+str(row_count)
                table_row = []
                table_row.append(row)
                table_row.append("A1:H3")
                #сделать формат всей таблицы - один шрифт - цвет - размер - убрать закраску
                worksheet.format(range_all, {
                    "backgroundColor": {
                        "red": 1.0,
                        "green": 1.0,
                        "blue": 1.0
                    },
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "foregroundColor": {
                            "red": 0.0,
                            "green": 0.0,
                            "blue": 0.0
                        },
                        "fontSize": 12,
                        "bold": False
                    }
                })
                #Изменнение структуры таблицы - текст черный, по центру, 12 шрифт, жирный (сам жирный)
                worksheet.format(table_row, {
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "foregroundColor": {
                            "red": 0.0,
                            "green": 0.0,
                            "blue": 0.0
                        },
                        "fontSize": 12,
                        "bold": True
                    }
                })

                logger.info(f" {message.from_user.username} do_things - Длина таблицы - {row_count}")

                mas = [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0],
                       [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0],
                       [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]

                name_disp = ['Жим гири', 'Мах гири', 'Отжимания', 'Пресс', 'Приседания', 'Приседания с гирей', 'Прыгающий Джек',
                             'Рывок гири', 'Скакалка', ]
                disp_end = [['Жим гири'], ['Мах гири'], ['Отжимания'], ['Пресс'], ['Приседания'], ['Приседания с гирей'], ['Прыгающий Джек'], ['Рывок гири'], ['Скакалка']] #для детей
                disp_end_man = [['Жим гири'], ['Мах гири'], ['Отжимания'], ['Пресс'], ['Приседания'], ['Приседания с гирей'], ['Прыгающий Джек'], ['Рывок гири'], ['Скакалка']] #для взрослых

                i = 4
                record_number = 0
                record_part = row_count - 6
                step_check = 0
                logger.info(f" {message.from_user.username} do_things - начало переборки")
                while i <= row_count:
                    len_value = len(list_of_lists[i-1][1])
                    if len_value >= 3:
                        step_check += 1
                        list_row_fixed.append(i-1)
                    if step_check == 1:  # МАЛЬЧИКИ
                        logger.info(f" {message.from_user.username} do_things - парсинг МАЛЬЧИКИ i = {i}")
                        cell_value = list_of_lists[i-1][3]
                        if cell_value == name_disp[0]:  # 1 ДИСЦЕПЛИНА
                            if list_of_lists[i - 1][4] == "":
                                disp_value = 0
                                range_error_colum.append("E"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[0][0] < disp_value:
                                    mas[0][0] = disp_value
                                    mas[0][1] = i
                        if cell_value == name_disp[1]:  # 2 ДИСЦЕПЛИНА
                            if list_of_lists[i - 1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[1][0] < disp_value:
                                    mas[1][0] = disp_value
                                    mas[1][1] = i
                        if cell_value == name_disp[2]:  # 3 ДИСЦЕПЛИНА
                            if list_of_lists[i - 1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[2][0] < disp_value:
                                    mas[2][0] = disp_value
                                    mas[2][1] = i
                        if cell_value == name_disp[3]:  # 4 ДИСЦЕПЛИНА
                            if list_of_lists[i - 1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[3][0] < disp_value:
                                    mas[3][0] = disp_value
                                    mas[3][1] = i
                        if cell_value == name_disp[4]:  # 5 ДИСЦЕПЛИНА
                            if list_of_lists[i - 1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[4][0] < disp_value:
                                    mas[4][0] = disp_value
                                    mas[4][1] = i
                        if cell_value == name_disp[5]:  # 6 ДИСЦЕПЛИНА
                            if list_of_lists[i - 1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[5][0] < disp_value:
                                    mas[5][0] = disp_value
                                    mas[5][1] = i
                        if cell_value == name_disp[6]:  # 7 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[6][0] < disp_value:
                                    mas[6][0] = disp_value
                                    mas[6][1] = i
                        if cell_value == name_disp[7]:  # 8 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[7][0] < disp_value:
                                    mas[7][0] = disp_value
                                    mas[7][1] = i
                        if cell_value == name_disp[8]:  # 9 ДИСЦЕПЛИНА
                            if list_of_lists[i - 1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[8][0] < disp_value:
                                    mas[8][0] = disp_value
                                    mas[8][1] = i
                    elif step_check == 2:  # ДЕВОЧКИ
                        logger.info(f" {message.from_user.username} do_things - парсинг ДЕВОЧКИ i = {i}")
                        cell_value = list_of_lists[i-1][3]
                        print(cell_value)
                        if cell_value == name_disp[0]:  # 1 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[9][0] < disp_value:
                                    mas[9][0] = disp_value
                                    mas[9][1] = i
                        if cell_value == name_disp[1]:  # 2 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[10][0] < disp_value:
                                    mas[10][0] = disp_value
                                    mas[10][1] = i
                        if cell_value == name_disp[2]:  # 3 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[11][0] < disp_value:
                                    mas[11][0] = disp_value
                                    mas[11][1] = i
                        if cell_value == name_disp[3]:  # 4 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[12][0] < disp_value:
                                    mas[12][0] = disp_value
                                    mas[12][1] = i
                        if cell_value == name_disp[4]:  # 5 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[13][0] < disp_value:
                                    mas[13][0] = disp_value
                                    mas[13][1] = i
                        if cell_value == name_disp[5]:  # 6 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[14][0] < disp_value:
                                    mas[14][0] = disp_value
                                    mas[14][1] = i
                        if cell_value == name_disp[6]:  # 7 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[15][0] < disp_value:
                                    mas[15][0] = disp_value
                                    mas[15][1] = i
                        if cell_value == name_disp[7]:  # 8 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[16][0] < disp_value:
                                    mas[16][0] = disp_value
                                    mas[16][1] = i
                        if cell_value == name_disp[8]:  # 9 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[17][0] < disp_value:
                                    mas[17][0] = disp_value
                                    mas[17][1] = i
                    if step_check == 3:  # Мужикииии
                        cell_value = list_of_lists[i-1][3]
                        logger.info(f" {message.from_user.username} do_things - парсинг МУЖИКИ i = {i}")
                        if cell_value == name_disp[0]:  # 1 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[18][0] < disp_value:
                                    mas[18][0] = disp_value
                                    mas[18][1] = i
                        if cell_value == name_disp[1]:  # 2 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[19][0] < disp_value:
                                    mas[19][0] = disp_value
                                    mas[19][1] = i
                        if cell_value == name_disp[2]:  # 3 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[20][0] < disp_value:
                                    mas[20][0] = disp_value
                                    mas[20][1] = i
                        if cell_value == name_disp[3]:  # 4 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[21][0] < disp_value:
                                    mas[21][0] = disp_value
                                    mas[21][1] = i
                        if cell_value == name_disp[4]:  # 5 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[22][0] < disp_value:
                                    mas[22][0] = disp_value
                                    mas[22][1] = i
                        if cell_value == name_disp[5]:  # 6 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[23][0] < disp_value:
                                    mas[23][0] = disp_value
                                    mas[23][1] = i
                        if cell_value == name_disp[6]:  # 7 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[24][0] < disp_value:
                                    mas[24][0] = disp_value
                                    mas[24][1] = i
                        if cell_value == name_disp[7]:  # 8 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[25][0] < disp_value:
                                    mas[25][0] = disp_value
                                    mas[25][1] = i
                        if cell_value == name_disp[8]:  # 9 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[26][0] < disp_value:
                                    mas[26][0] = disp_value
                                    mas[26][1] = i
                    elif step_check == 4:  # Женщины
                        logger.info(f" {message.from_user.username} do_things - парсинг ЖЕНЩИНЫ i = {i}")
                        cell_value = list_of_lists[i-1][3]
                        if cell_value == name_disp[0]:  # 1 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[27][0] < disp_value:
                                    mas[27][0] = disp_value
                                    mas[27][1] = i
                        if cell_value == name_disp[1]:  # 2 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[28][0] < disp_value:
                                    mas[28][0] = disp_value
                                    mas[28][1] = i
                        if cell_value == name_disp[2]:  # 3 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[29][0] < disp_value:
                                    mas[29][0] = disp_value
                                    mas[29][1] = i
                        if cell_value == name_disp[3]:  # 4 ДИС
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[30][0] < disp_value:
                                    mas[30][0] = disp_value
                                    mas[30][1] = i
                        if cell_value == name_disp[4]:  # 5 ДИС
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[31][0] < disp_value:
                                    mas[31][0] = disp_value
                                    mas[31][1] = i
                        if cell_value == name_disp[5]:  # 6 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[32][0] < disp_value:
                                    mas[32][0] = disp_value
                                    mas[32][1] = i
                        if cell_value == name_disp[6]:  # 7 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[33][0] < disp_value:
                                    mas[33][0] = disp_value
                                    mas[33][1] = i
                        if cell_value == name_disp[7]:  # 8 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[34][0] < disp_value:
                                    mas[34][0] = disp_value
                                    mas[34][1] = i
                        if cell_value == name_disp[8]:  # 9 ДИСЦЕПЛИНА
                            if list_of_lists[i-1][4] == "":
                                disp_value = 0
                                range_error_colum.append("C"+str(i))
                            else:
                                disp_value = int(list_of_lists[i-1][4])
                                if mas[35][0] < disp_value:
                                    mas[35][0] = disp_value
                                    mas[35][1] = i
                    i += 1
                i = 0  ### Вывод ииимен с помощью массива mas
                logger.info(f" {message.from_user.username} do_things - значение mas после фильтра - {mas}")
                x = 0
                mas_name = [[0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0],[0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0]]
                ob = 1

                while i < len(mas):
                    trupp = int(mas[x][1])
                    if trupp > 0:
                        logger.info(f" {message.from_user.username} do_things - отбор значений для покраски и рекордсменов, строка - {trupp}")
                        ranges = "C" + str(trupp)+ ":H"+ str(trupp)
                        record_number += 1
                        ranges_to_color.append(ranges)
                        top_value = list_of_lists[trupp-1][2] + ' ' + list_of_lists[trupp-1][3] + ' - ' + list_of_lists[trupp-1][4]
                        top_name = list_of_lists[trupp-1][2] + ' - ' + list_of_lists[trupp-1][4]
                        print(str(ob) + ' ' + top_value)
                        if len(mas[x]) > 1:
                            if i <= 8 or (i >=18 and i <= 26):
                                mas_name[x] = ("М: " + top_name + "\n")
                            else:
                                mas_name[x] = ("Ж: " + top_name + "\n")


                    i += 1
                    ob += 1
                    x += 1


                #переборка переделать потом:
                i = 0

                category_man = "\n\n<b>Категория от 18 включительно</b>\n"
                category_boy = "\n\n<b>Категория от 8 до 17</b>\n"

                s = 0
                sm = 0
                while i < len(mas_name):

                    logger.info(f" {message.from_user.username} do_things - mas_name[{i}] = {mas_name[i]}")
                    print(mas_name[i])
                    if len(mas_name[i]) <= 3:
                        mas_name[i] = ""
                        print(mas_name[i])
                    if i <= 8 and len(mas_name[i]) <= 3 and len(mas_name[i+9]) <= 3:
                        disp_end[i] = ""
                    if i <= 8 and len(mas_name[i+18]) <= 3 and len(mas_name[i+27]) <= 3:
                        disp_end_man[i] = ""
                    if i <=8 and len(mas_name[i]) <= 3 and len(mas_name[i+9]) <= 3:
                        sm += 1
                    if i >= 18 and i <= 26 and len(mas_name[i]) <= 3 and len(mas_name[i+9]) <= 3:
                        s += 1
                    i += 1
                    if s == 9:
                        category_man = ""
                    if sm == 9:
                        category_boy = ""
                i = 0
                number = 1
                while i <= 8:
                    if disp_end[i] != "":
                        disp_end[i] = "\n"+str(number)+". <i>"+name_disp[i]+":</i>\n"
                        number += 1
                    i += 1
                i = 0
                number = 1
                while i <= 8:
                    if disp_end_man[i] != "":
                        disp_end_man[i] = "\n" + str(number) + ". <i>" + name_disp[i] + ":</i>\n"
                        number += 1
                    i += 1
                logger.info(f" {message.from_user.username} do_things - disp_end = {disp_end}")
                logger.info(f" {message.from_user.username} do_things - подключение к БД ")
                conn = sqlite3.connect(DataBaseFile)
                cursor = conn.cursor()
                people_id = message.chat.id
                cursor.execute(f"SELECT locatename FROM info WHERE id = {people_id}")
                res = cursor.fetchone()[0]
                user_location = str(res)

                logger.info(f" {message.from_user.username} do_things - взял имя локации из БД - {user_location}")
                conn.commit()
                logger.info(f" {message.from_user.username} do_things - отключение соединения с БД ")

                bot.send_message(message.chat.id, "<b>📍Локация: "+user_location+"</b>\n\n🔝Рекордсмены дня от "+current_date+category_boy+disp_end[0]+mas_name[0] + mas_name[9]+disp_end[1]+mas_name[1] + mas_name[10]+disp_end[2]+mas_name[2] + mas_name[11]+disp_end[3]+mas_name[3] + mas_name[12]+disp_end[4]+mas_name[4] + mas_name[13]+disp_end[5]+mas_name[5] + mas_name[14]+disp_end[6]+mas_name[6] + mas_name[15]+disp_end[7]+mas_name[7] + mas_name[16]+disp_end[8]+mas_name[8] + mas_name[17]+category_man+disp_end_man[0]+mas_name[18] + mas_name[27]+disp_end_man[1]+mas_name[19] + mas_name[28]+disp_end_man[2]+mas_name[20] + mas_name[29]+disp_end_man[3]+mas_name[21] + mas_name[30]+disp_end_man[4]+mas_name[22] + mas_name[31]+disp_end_man[5]+mas_name[23] + mas_name[32]+disp_end_man[6]+mas_name[24] + mas_name[33]+disp_end_man[7]+mas_name[25] + mas_name[34]+disp_end_man[8]+mas_name[26] + mas_name[35]+"\n", parse_mode='HTML')
                # bot.send_message(message.chat.id, 'Локация: Сквер у Гольяновского пруда м.Щёлковская Рекордсмены дня от 10.09.2023Категория от 8 до 17          1. Жим гири:М: Эркеев Эрлан - 57Ж: Оводова Глафира - 47   2. Махи гири:          М: Эспандеров Азиз - 48Ж: Казанцева Ева - 43      3. Отжимания:      М: Алозай Захар - 43Ж: Чеботарь Александра - 61 4. Пресс :           М: Мамврийский Георгий - 42Ж: Мозгова Арина - 57   5. Приседания:   М: Магомедов Ибадулла - 65Ж: Осадыча Яна - 53        6. Приседания с гирей:       М: Хуменков Александр - 45Ж: Велич Таисия - 46          7. Прыжок в длину:М: Сидорочев Тимофей - 1,92Ж: Чарыкова Арина - 1,90 8. Рывок Гири: М: Канатбеков Нурел - 28Ж: Елисеева Надежда - 259. Скакалка:М: Акрам Абдукадиров - 154Ж: Любакова Софья - 193Категория от 18 включительно1. Жим гири:М: Евглевский Федор - 66Ж: Сиваченко Мария - 25   2. Махи гири:          М: Лунёв Сергей - 42Ж: Желобанова Светлана - 47      3. Отжимания:      М: Наумов Андрей - 47Ж: Несмашная Альбина - 25 4. Пресс :           М: Малаханов Дмитрий - 50Ж: Хубежова Анастасия - 42   5. Приседания:   М: Оводов Василий - 51Ж: Чириповская Елена - 48        6. Приседания с гирей:       М: Яблоков Артем - 55Ж: Чеботарь Валерия - 40          7. Прыжок в длину:М: Любаков Семен - 2,15Ж: Шемчук Любовь - 1,84 8. Рывок Гири: М: Карнауков Константин - 30Ж: Оводова Ирина - 319. Скакалка:М: Бурлак Евгений - 201Ж: Липатова Татьяна - 153', parse_mode="MarkdownV2")
                logger.info(f" {message.from_user.username} do_things - Отправил список рекордсменов пользователю!! id = {message.chat.id}")

                ##############################
                #Покраска черных отступов
                ##############################
                logger.info(f" {message.from_user.username} do_things - Номера строк list_row_fixed = {list_row_fixed}")
                range_row_fixed = []
                l = 1
                while l <= 3:
                    if l == 2:
                        range_row_fixed.append("A" + str(list_row_fixed[l]) + ":C" + str(list_row_fixed[l]))
                    else:
                        range_row_fixed.append("B"+str(list_row_fixed[l])+":C"+str(list_row_fixed[l]))
                    l += 1

                worksheet.format(range_row_fixed, {
                    "backgroundColor": {
                        #0.2627451, 0.2627451, 0.2627451
                        "red": 0.2627451,
                        "green": 0.2627451,
                        "blue": 0.2627451

                    },
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "foregroundColor": {
                        #0.2627451, 0.2627451, 0.2627451
                        "red": 0.2627451,
                        "green": 0.2627451,
                        "blue": 0.2627451
                        },
                        "fontSize": 10,
                        "bold": False
                    }
                })


                ##############################
                #ПОКРАСКА ТАБЛИЦЫ В ЗЕЛЕНЫЙ
                ##############################

                logger.info(f" {message.from_user.username} do_things - Список для покраски - {ranges_to_color}")
                #RGB: 0.8509804, 0.91764706, 0.827451
                worksheet.format(ranges_to_color, {
                    "backgroundColor": {
                        "red": 0.8509804,
                        "green": 0.91764706,
                        "blue": 0.827451

                    },
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "foregroundColor": {
                            "red": 0.0,
                            "green": 0.0,
                            "blue": 0.0
                        },
                        "fontSize": 12,
                        "bold": False
                    }
                })
                range_row_fixed.clear()
                list_row_fixed.clear()
                ranges_to_color.clear()
                table_row.clear()

                logger.info(f" {message.from_user.username} do_things - очистка списка покраски - {ranges_to_color}")
                logger.info(f" {message.from_user.username} do_things - Покрасил таблицу - ")






                # whil??print?ie i < len(mas_name):
                # print(mas_name[19])
                # i = 1
                #     if len(mas_name[i-1]) > 1:
                #         if i <=8 or i > 27:
                #             print("М: "+mas_name[i-1])
                #         else:
                #             print("Ж: " + mas_name[i - 1])
                #     i += 1
                logger.info(f" {message.from_user.username} do_things - mas_name - {mas_name}")
                if not range_error_colum:
                    logger.info(f" {message.from_user.username} do_things - все строки заполнены range_error - {range_error_colum}")
                    bot.send_message(message.chat.id, "Список рекордсменов готов, проверяйте.")
                else:
                    bot.send_message(message.chat.id, f"Замечена пустая строка, список рекордсменов может быть не точным! Проверьте ячейки - {range_error_colum}")
                bot.send_message(message.chat.id, f"Всего записей в таблице - <b>{record_part}</b>, рекордсменов - <b>{record_number}</b>", parse_mode='HTML')
            else:
                bot.send_message(message.chat.id, "Проверьте 2 столбец (муж - жен). Шаблон:")
                #bot.send_photo(message.chat.id, img = open('/template.png','rb'))
                bot.send_photo(photo = InputFile(f'/template.png'), chat_id=message.chat.id)
        except Exception as e:
            bot.send_message(message.chat.id, f"Ну пиздец сломали...(Произошла ошибка при обработке): {str(e)}")
            err = str(e)
            logger.error(f"do_things - Ошибка у {message.chat.id} ошибка - {str(e)}")

# Функция для создания клавиатуры с кнопками
def create_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('Настройки', 'Сделать вещи')
    return markup











# Метод, который будет вызываться при получении обновлений
@app.route('/', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return '', 200

# Установка вебхука
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_HOST)

if __name__ == '__main__':
    set_webhook()
    app.run(host=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
            ssl_context=('/etc/letsencrypt/live/etedsfeqa.ru/fullchain.pem', '/etc/letsencrypt/live/etedsfeqa.ru/privkey.pem'))
