import logging
import config
import telebot
import sqlite3
import datetime
import requests
from telebot import types

bot = telebot.TeleBot(config.token)
user_data = {"phone": "", "name": "", "user_age": 0, "address": ""}
complaint_data = {"idcat": 0, "place": "", "address": "", "photo": "", "comment": "", "thanks": ""}

logging.basicConfig(filename=config.log_name,
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%d.%m.%Y %H:%M:%S')
logging.info("create object telebot")
logging.info("bot connect to database")

def get_Time_Now():
    return datetime.datetime.strftime(datetime.datetime.now(), "%d.%m.%Y %H:%M:%S")

def get_from_DB(sql):
    conn = sqlite3.connect(config.db_name)
    cursor = conn.cursor()

    cursor.execute(sql)
    return cursor.fetchall()

    conn.close()

def oper_with_DB(sql):
    conn = sqlite3.connect(config.db_name)
    cursor = conn.cursor()
    #try:
    cursor.execute(sql)
    conn.commit()
    conn.close()
    return True
    #except:
    #    return False

@bot.message_handler(commands=["start"])
def start(message):
    data = get_from_DB("SELECT * from registered_user WHERE uid_telegram=%i" % message.from_user.id)
    if not data:
        get_num(message)
    else:
        if data[0][7] == 1:
            start_user_panel(message, data[0][2])
        else:
            bot.send_message(message.chat.id, "Ваша заявка еще не одобрена.")

def get_num(message):
    buttons = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    buttons.add(*[types.KeyboardButton("Отправить номер", request_contact=True)])
    bot.send_message(message.chat.id, get_from_DB("SELECT text FROM text_for_user WHERE id=1")[0], reply_markup=buttons)
    bot.register_next_step_handler(message, get_location)

def get_location(message):
    global user_data
    user_data["phone"] = message.contact.phone_number
    buttons = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    buttons.add(*[types.KeyboardButton("Отправить местоположение", request_location=True)])
    bot.send_message(message.chat.id, get_from_DB("SELECT text FROM text_for_user WHERE id=2")[0], reply_markup=buttons)
    bot.register_next_step_handler(message, get_name_street)

def get_name_street(message):
    global user_data
    location = "%s,%s" % (message.location.latitude,message.location.longitude)
    address = requests.get("https://maps.googleapis.com/maps/api/geocode/json?latlng=%s&key=%s&language=ru" %
                           (location, config.google_apikey)).json()['results'][0]['formatted_address']
    user_data["address"] = address
    buttons = types.InlineKeyboardMarkup()
    buttons.add(*[types.InlineKeyboardButton(name, callback_data=name) for name in ["Да", "Нет"]])
    bot.send_message(message.chat.id, "Ваш адрес: %s?" % address, reply_markup=buttons)

@bot.callback_query_handler(func=lambda c:True)
def validation_address(c):
    if c.data == "Да":
        get_name(c.message)
    elif c.data == "Нет":
        bot.send_message(c.message.chat.id, "Введите адрес: ")
        bot.register_next_step_handler(c.message, user_input_valid_address)

def user_input_valid_address(message):
    user_data["address"] = message.text
    get_name(message)

def get_name(message):
    bot.send_message(message.chat.id, get_from_DB("SELECT text FROM text_for_user WHERE id=3")[0])
    bot.register_next_step_handler(message, get_age)

def get_age(message):
    global user_data
    user_data["name"] = message.text
    bot.send_message(message.chat.id, get_from_DB("SELECT text FROM text_for_user WHERE id=5")[0])
    bot.register_next_step_handler(message, validation_user)

def validation_user(message):
    global user_data
    user_data["user_age"] = int(message.text)
    buttons = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons.add(types.KeyboardButton("Подтверждаю"), types.KeyboardButton("Сначала"))
    bot.send_message(message.chat.id, '''Номер телефона: %s
Имя: %s
Адрес: %s
Возраст: %i
    
Если данные вверны, нажмите Подтверждаю для регистрации''' %
                     (user_data["phone"], user_data["name"], user_data["address"], user_data["user_age"]),
                     reply_markup=buttons)
    bot.register_next_step_handler(message, register_user)

def register_user(message):
    global user_data
    if message.text == "Подтверждаю":
        if oper_with_DB("INSERT INTO registered_user VALUES (NULL,%i,'%s','%s','%s',%i,'%s', 0)" %
                        (message.from_user.id, user_data["name"], user_data["phone"],
                         user_data["address"], user_data["user_age"], get_Time_Now())):
            bot.send_message(message.chat.id, get_from_DB("SELECT text FROM text_for_user WHERE id=7")[0])
        else:
            bot.send_message(message.chat.id, get_from_DB("SELECT text FROM text_for_user WHERE id=8")[0])
    elif message.text == "Сначала":
        get_num(message)
    else:
        bot.register_next_step_handler(message, register_user)

def start_user_panel(message, uname):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(*[types.KeyboardButton(name[1]) for name in get_from_DB("SELECT * FROM buttons_name LIMIT 4")])
    bot.send_message(message.chat.id, "%s можете выбрать необходимую функцию: " % uname, reply_markup=keyboard)
    bot.register_next_step_handler(message, choise_user)

def choise_user(message):
    if (message.text == get_from_DB("SELECT * FROM buttons_name WHERE id=3")[0][1]):
        button = types.InlineKeyboardMarkup()
        button.add(types.InlineKeyboardButton(text = "Подробнее", url = "http://telegra.ph/O-proekte-05-11"))
        bot.send_message(message.chat.id, "Клуб Активистов города, которым не все равно, где жить. Этот ...",
                         reply_markup=button)
    if (message.text == get_from_DB("SELECT * FROM buttons_name WHERE id=4")[0][1]):
        buttons = types.ReplyKeyboardMarkup(resize_keyboard=True,one_time_keyboard=True,row_width=2)
        user_cat = get_from_DB("SELECT * FROM user_cat WHERE uid_telegram = %s" % message.from_user.id)
        if (user_cat):
            buttons.add(*[types.KeyboardButton(name[1]) for name in user_cat])
        else:
            buttons.add(*[types.KeyboardButton(name[1]) for name in get_from_DB("SELECT * FROM categories LIMIT 3")],
                        types.KeyboardButton(get_from_DB("SELECT text FROM buttons_name WHERE id=7")[0][0]),
                        types.KeyboardButton(get_from_DB("SELECT text FROM buttons_name WHERE id=8")[0][0]))
        bot.send_message(message.chat.id, get_from_DB("SELECT text FROM text_for_user WHERE id=10")[0], reply_markup=buttons)
        bot.register_next_step_handler(message, work_with_cat)
    else:
        bot.register_next_step_handler(message, choise_user)

def work_with_cat(message):
    if (message.text == get_from_DB("SELECT text FROM buttons_name WHERE id=7 ")[0][0]):
        categories = get_from_DB("SELECT * FROM categories")
        strcat = "Введите номер категории: \n"
        for cat in categories:
            strcat += str(cat[0]) + ". " + cat[1] + "\n"
        bot.send_message(message.chat.id, strcat)
        bot.register_next_step_handler(message, choise_place)


def choise_place(message):
    global complaint_data
    try:
        complaint_data["idcat"] = int(message.text)
    except:
        complaint_data["idcat"] = 1
    print(message)

try:
    bot.polling(none_stop=True)
except:
    logging.error("bot polling stop")