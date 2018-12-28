# -*- coding: utf-8 -*-
import mysql.connector
from telegram.ext import RegexHandler, CommandHandler, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler
import telegram
import re

chortke_bot = telegram.Bot(token='590929905:AAHvs0m18qm_g84NKQXyWbQC_K9lmu5uYbs')

import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

chortke_db = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="97546102",
    database="chortke_database"
)

ch_cursor = chortke_db.cursor()

menu_keyboard = [['ایجاد تراکنش', 'مشاهده تراکنش ها'],
                 ['عضویت در گروه', 'ایجاد گروه']]
reply_keyboard = telegram.ReplyKeyboardMarkup(keyboard=menu_keyboard, 
                                              one_time_keyboard=True,
                                              resize_keyboard=True)

menu_keyboard =  telegram.ReplyKeyboardMarkup(keyboard=[['منوی اصلی']], 
                                              one_time_keyboard=True,
                                              resize_keyboard=True)                                             

MainMenu, ShowTransaction, CreateTransaction, \
CreateGroup, JoinGroup, CreateIncome,\
CreateCost, CreateDebt= range(8)


def start(bot, update):
    update.message.reply_text('لطفا گزینه مورد نظر را انتخاب کنید.', reply_markup=reply_keyboard)
    sql = "SELECT user_id FROM chortke_database.users WHERE user_id = %s"
    ch_cursor.execute(sql, (update.effective_user.id,))
    result = ch_cursor.fetchall()
    if len(result) == 0:
        sql = "INSERT INTO chortke_database.users (user_id, user_name) VALUES (%s, %s)"
        if(update.effective_user.username == None):
            values = (update.effective_user.id, update.effective_user.full_name)
        else:
            values = (update.effective_user.id, update.effective_user.username)
        ch_cursor.execute(sql, values)
        chortke_db.commit()

    return MainMenu


create_group_state = 0


def create_group(bot, update, user_data):
    global create_group_state

    if create_group_state == 0:
        update.message.reply_text('لطفا شناسه یا id گروه را وارد کنید')
        create_group_state += 1
        return CreateGroup

    if create_group_state == 1:
        user_data['group_id'] = update.message.text
        update.message.reply_text('لطفا نام گروه را وارد کنید')

    if create_group_state == 2:
        user_data['group_name'] = update.message.text
        update.message.reply_text('لطفا رمز گروه را مشخص کنید')

    if create_group_state == 3:
        group_password = update.message.text
        group_owner_id = update.effective_user.id
        sql = "INSERT INTO chortke_database.groups (gp_id, gp_name, gp_password, gp_owner_id) VALUES (%s, %s, %s, %s)"
        val = (user_data['group_id'], user_data['group_name'], group_password, group_owner_id)
        ch_cursor.execute(sql, val)
        chortke_db.commit()
        sql = "INSERT INTO chortke_database.gp_members (gp_id, user_id) VALUES (%s, %s)"
        values = (user_data['group_id'], group_owner_id)
        ch_cursor.execute(sql, values)
        chortke_db.commit()
        update.message.reply_text('گروه با موفقیت ایجاد شد.می توانید id و رمز عبور را برای اعضا ارسال کنید.',
                                  reply_markup=reply_keyboard)
        create_group_state = 0
        return MainMenu

    create_group_state += 1


join_group_state = 0


def join_group(bot, update, user_data):
    global join_group_state

    if join_group_state == 0:
        update.message.reply_text('لطفا شناسه یا id گروه را وارد کنید')
        join_group_state += 1
        return JoinGroup

    if join_group_state == 1:
        user_data['join_group_id'] = update.message.text
        sql = "SELECT gp_id FROM chortke_database.groups WHERE gp_id = %s"
        ch_cursor.execute(sql, (user_data['join_group_id'],))
        result = ch_cursor.fetchall()
        if len(result) == 0:
            update.message.reply_text('گروهی با این شناسه ثبت نشده است.لطفا دوباره شناسه را وارد کنید.')
            return JoinGroup
        else:
            update.message.reply_text('لطفا رمز عبور را وارد کنید')

    if join_group_state == 2:
        sql = "SELECT gp_password FROM chortke_database.groups WHERE gp_password = %s and gp_id = %s"
        gp_password = update.message.text
        values = (gp_password, user_data['join_group_id'],)
        ch_cursor.execute(sql, values)
        result = ch_cursor.fetchall()
        if len(result) == 0:
            update.message.reply_text('رمز عبور اشتباه می باشد.لطفا دوباره رمز را وارد کنید.')
            return JoinGroup
        else:
            sql = "INSERT INTO chortke_database.gp_members (gp_id, user_id) VALUES (%s, %s)"
            values = (user_data['join_group_id'], update.effective_user.id)
            ch_cursor.execute(sql, values)
            chortke_db.commit()
            update.message.reply_text('شما با موفقیت در گروه عضو شدید', reply_markup=reply_keyboard)
            join_group_state = 0
            return MainMenu

    join_group_state += 1


def create_transaction(bot, update):
    update.message.reply_text('لطفا نوع تراکنش را مشخص کنید',
                              reply_markup=telegram.ReplyKeyboardMarkup(
                                  keyboard=[['درآمد', 'هزینه'], ['بدهکاری', 'طلبکاری'], ['منوی اصلی']],
                                  one_time_keyboard=True,
                                  resize_keyboard=True
                              )
                              )
    return CreateTransaction


def show_transaction(bot, update):
    sql = "SELECT income_title, income, DATE_FORMAT(income_date, '%T %d-%m-%Y') FROM chortke_database.income WHERE user_id = %s"
    ch_cursor.execute(sql, (update.effective_user.id, ))
    incomes = ch_cursor.fetchall()

    sql = "SELECT cost_title, cost, DATE_FORMAT(cost_date, '%T %d-%m-%Y') FROM chortke_database.cost WHERE user_id = %s"
    ch_cursor.execute(sql, (update.effective_user.id, ))
    costs = ch_cursor.fetchall()

    sql = "SELECT chortke_database.debtor_creditor.debt_title, chortke_database.debtor_creditor.debt, DATE_FORMAT(chortke_database.debtor_creditor.debt_date,'%T %d-%m-%Y'), chortke_database.users.user_name FROM chortke_database.debtor_creditor INNER JOIN chortke_database.users ON chortke_database.debtor_creditor.debtor_id = chortke_database.users.user_id WHERE chortke_database.debtor_creditor.creditor_id = %s"
    ch_cursor.execute(sql, (update.effective_user.id, ))
    talabkariha = ch_cursor.fetchall()

    sql = "SELECT chortke_database.debtor_creditor.debt_title, chortke_database.debtor_creditor.debt, DATE_FORMAT(chortke_database.debtor_creditor.debt_date, '%T %d-%m-%Y'), chortke_database.users.user_name FROM chortke_database.debtor_creditor INNER JOIN chortke_database.users ON chortke_database.debtor_creditor.creditor_id = chortke_database.users.user_id WHERE chortke_database.debtor_creditor.debtor_id = %s"
    ch_cursor.execute(sql, (update.effective_user.id, ))
    bedehkariha = ch_cursor.fetchall()


    total_transaction = 0

    income_text = "🔹درآمد ها : \n\n"
    if len(incomes) == 0:
        income_text += "درآمدی ثبت نشده است." + "\n\n"
    else:
        for i in range(0, len(incomes)):
            income_text += "مبلغ :   " + str(incomes[i][1]) + " تومان" + "\n" + \
                        "تاریخ :   " + incomes[i][2] + "\n" + \
                        "عنوان :   " + incomes[i][0] + "\n\n"
            total_transaction += int(incomes[i][1])

    income_text += "@Chortke23_bot"
    update.message.reply_text(income_text)


    cost_text = "🔹هزینه ها : \n\n"
    if len(costs) == 0:
        cost_text += "هزینه ای ثبت نشده است." + "\n\n"
    else:
        for i in range(0, len(costs)):
            cost_text += "مبلغ :   " + str(costs[i][1]) + " تومان" + "\n" + \
                        "تاریخ :   " + costs[i][2] + "\n" + \
                        "عنوان :   " + costs[i][0] + "\n\n"
            total_transaction -= int(costs[i][1])

    cost_text += "@Chortke23_bot"
    update.message.reply_text(cost_text)

    
    bedehkari_text = "🔹بدهکاری ها : \n\n"
    if len(bedehkariha) == 0:
        bedehkari_text += "بدهکاری ثبت نشده است." + "\n\n"
    else:
        for i in range(0, len(bedehkariha)):
            bedehkari_text += "عنوان :   " + bedehkariha[i][0] + "\n" + \
                            "مبلغ :   " + str(bedehkariha[i][1]) + " تومان" + "\n" + \
                            "تاریخ :   " + bedehkariha[i][2] + "\n" + \
                            "طلبکار :   " + bedehkariha[i][3] + "\n\n"
            total_transaction -= int(bedehkariha[i][1])

    bedehkari_text += "@Chortke23_bot"
    update.message.reply_text(bedehkari_text)


    talabkari_text = "🔹طلبکاری ها : \n\n"
    if len(talabkariha) == 0:
        talabkari_text += "طلبکاری ثبت نشده است." + "\n\n"
    else:
        for i in range(0, len(talabkariha)):
            talabkari_text += "عنوان :   " + talabkariha[i][0] + "\n" + \
                            "مبلغ :   " + str(talabkariha[i][1]) + " تومان" + "\n" + \
                            "تاریخ :   " + talabkariha[i][2] + "\n" + \
                            "بدهکار :   " + talabkariha[i][3] + "\n\n"
            total_transaction += int(talabkariha[i][1])
    talabkari_text += "@Chortke23_bot"
    update.message.reply_text(talabkari_text)


    update.message.reply_text("\n" + "مجموع تراکنش ها : " + "\n" + str(total_transaction) + " Toman" + "\n\n" + "@Chortke23_bot", reply_markup=reply_keyboard)
    return MainMenu


create_debt_state = 0


def create_debt(bot, update, user_data):
    global create_debt_state, debt

    if create_debt_state == 0:
        if re.match(r'^(بدهکاری)$', update.message.text):
            debt = True
        elif re.match(r'^(طلبکاری)$', update.message.text):
            debt = False

        sql = "SELECT chortke_database.groups.gp_name, chortke_database.gp_members.gp_id FROM chortke_database.gp_members inner join chortke_database.groups ON chortke_database.gp_members.gp_id = chortke_database.groups.gp_id WHERE user_id = %s"
        ch_cursor.execute(sql, (update.effective_user.id, ))
        groups = ch_cursor.fetchall()
        gp_keyboard = []
        for x in range(0, len(groups)):
            groups[x] = groups[x][0] + " : " + groups[x][1]
        for i in range(0, len(groups), 2):
            gp_keyboard.append(groups[i:i+2])
        gp_keyboard.append(['منوی اصلی'])
        update.message.reply_text(text='لطفا گروه مورد نظر را انتخاب کنید',
                                  reply_markup=telegram.ReplyKeyboardMarkup(keyboard=gp_keyboard, 
                                                                            one_time_keyboard=True,
                                                                            resize_keyboard=True))
        create_debt_state += 1
        return CreateDebt                      

    if create_debt_state == 1:
        user_data['gp_id'] = update.message.text.split(' : ', 2)[1]
        update.message.reply_text(text='لطفا مبلغ را وارد کنید',
                                  reply_markup=telegram.ReplyKeyboardMarkup(keyboard=[['منوی اصلی']],
                                                                            resize_keyboard=True))

    if create_debt_state == 2:
        user_data['debt'] = int(update.message.text)

        sql = "SELECT user_name, chortke_database.users.user_id FROM chortke_database.users inner join chortke_database.gp_members ON chortke_database.users.user_id = chortke_database.gp_members.user_id WHERE gp_id = %s and chortke_database.gp_members.user_id != %s "
        ch_cursor.execute(sql, (user_data['gp_id'], update.effective_user.id, ))
        users = ch_cursor.fetchall()
        user_keyboard = []
        for x in range(0, len(users)):
            users[x] = telegram.InlineKeyboardButton(text=users[x][0], callback_data=users[x][1])
        for i in range(0, len(users), 2):
            user_keyboard.append(users[i:i + 2])   
        update.message.reply_text(text='لطفا فرد مورد نظر را انتخاب کنید',
                                  reply_markup=telegram.InlineKeyboardMarkup(inline_keyboard=user_keyboard))

    if create_debt_state == 3:
        u_id = update.callback_query.from_user.id
        if debt:
            user_data['creditor_id'] = update.callback_query.data
            chortke_bot.sendMessage(chat_id=u_id, text='لطفا عنوان بدهکاری را وارد کنید', 
                                    reply_markup=telegram.ReplyKeyboardMarkup(keyboard=[['منوی اصلی']],
                                                                              one_time_keyboard=True,
                                                                              resize_keyboard=True))
        else:
            user_data['debtor_id'] = update.callback_query.data
            chortke_bot.sendMessage(chat_id=u_id, text='لطفا عنوان طلبکاری را وارد کنید',
                                    reply_markup=telegram.ReplyKeyboardMarkup(keyboard=[['منوی اصلی']],
                                                                              one_time_keyboard=True,
                                                                              resize_keyboard=True))                                  

    if create_debt_state == 4:
        user_data['debt_title'] = update.message.text

        sql = "INSERT INTO chortke_database.debtor_creditor (gp_id, creditor_id, debtor_id, debt, debt_title, debt_date) VALUES (%s, %s, %s, %s, %s, now())"
        if debt:
            values = (user_data['gp_id'], user_data['creditor_id'], update.effective_user.id, user_data['debt'],
                      user_data['debt_title'])
        else:
            values = (user_data['gp_id'], update.effective_user.id, user_data['debtor_id'], user_data['debt'],
                      user_data['debt_title'])
        ch_cursor.execute(sql, values)
        chortke_db.commit()

        update.message.reply_text('اطلاعات با موفقیت ثبت شد', reply_markup=reply_keyboard)
        create_debt_state = 0
        return MainMenu

    create_debt_state += 1


create_cost_state = 0


def create_cost(bot, update, user_data):
    global create_cost_state

    if create_cost_state == 0:
        update.message.reply_text('لطفا عنوان هزینه را وارد کنید', reply_markup=menu_keyboard)
        create_cost_state += 1
        return CreateCost

    if create_cost_state == 1:
        user_data['cost_title'] = update.message.text
        update.message.reply_text('لطفا مبلغ هزینه را وارد کنید', reply_markup=menu_keyboard)

    if create_cost_state == 2:
        user_data['cost'] = update.message.text
        user_data['cost_user_id'] = update.effective_user.id
        sql = "INSERT INTO chortke_database.cost (user_id, cost_title, cost, cost_date) VALUES (%s, %s, %s, now())"
        ch_cursor.execute(sql, (user_data['cost_user_id'],
                                user_data['cost_title'],
                                user_data['cost'],))
        chortke_db.commit()
        update.message.reply_text('با موفقیت ثبت شد', reply_markup=reply_keyboard)
        create_cost_state = 0
        return MainMenu

    create_cost_state += 1


create_income_state = 0


def create_income(bot, update, user_data):
    global create_income_state

    if create_income_state == 0:
        update.message.reply_text('لطفا عنوان درآمد را وارد کنید', reply_markup=menu_keyboard)
        create_income_state += 1
        return CreateIncome

    if create_income_state == 1:
        user_data['income_title'] = update.message.text
        update.message.reply_text('لطفا مبلغ درآمد را وارد کنید', reply_markup=menu_keyboard)

    if create_income_state == 2:
        user_data['income'] = update.message.text
        user_data['income_user_id'] = update.effective_user.id
        sql = "INSERT INTO chortke_database.income (user_id, income_title, income, income_date) VALUES (%s, %s, %s, now())"
        ch_cursor.execute(sql, (user_data['income_user_id'],
                                user_data['income_title'],
                                user_data['income'],))
        chortke_db.commit()
        update.message.reply_text('با موفقیت ثبت شد', reply_markup=reply_keyboard)
        create_income_state = 0
        return MainMenu

    create_income_state += 1


def menu(bot, update):
    global create_income_state, create_cost_state, create_debt_state
    update.message.reply_text('لطفا گزینه مورد نظر را انتخاب کنید.', reply_markup=reply_keyboard)
    create_income_state = 0
    create_cost_state = 0 
    create_debt_state = 0
    return MainMenu


# i = 0
# def temp(bot, update):
#     global i
#     print(update.message.audio)
#     update.message.audio.get_file().download()
#     print(i)
#     i += 1


def main():
    updater = telegram.ext.Updater(token='590929905:AAHvs0m18qm_g84NKQXyWbQC_K9lmu5uYbs')
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            MainMenu: [RegexHandler('^(مشاهده)\s(تراکنش)\s(ها)$', show_transaction),
                       RegexHandler('^(ایجاد)\s(تراکنش)$', create_transaction),
                       RegexHandler('^(ایجاد)\s(گروه)$', create_group, pass_user_data=True),
                       RegexHandler('^(عضویت)\s(در)\s(گروه)$', join_group, pass_user_data=True)
                       ],
            ShowTransaction: [MessageHandler(Filters.text, show_transaction)],
            CreateTransaction: [RegexHandler('^(هزینه)$', create_cost, pass_user_data=True),
                                RegexHandler('^(درآمد)$', create_income, pass_user_data=True),
                                RegexHandler('^(منوی)\s(اصلی)$', menu),
                                MessageHandler(Filters.text, create_debt, pass_user_data=True)
                               ],
            CreateGroup: [MessageHandler(Filters.text, create_group, pass_user_data=True)],
            JoinGroup: [MessageHandler(Filters.text, join_group, pass_user_data=True)],
            CreateCost: [RegexHandler('^(منوی)\s(اصلی)$', menu),
                         MessageHandler(Filters.text, create_cost, pass_user_data=True)],
            CreateIncome: [RegexHandler('^(منوی)\s(اصلی)$', menu),
                           MessageHandler(Filters.text, create_income, pass_user_data=True)
                          ],
            CreateDebt: [RegexHandler('^(منوی)\s(اصلی)$', menu),
                         CallbackQueryHandler(create_debt,pass_user_data=True),
                         MessageHandler(Filters.text, create_debt, pass_user_data=True)]
        },

        fallbacks=[]
    )

    dispatcher.add_handler(conv_handler)

    # t = MessageHandler(Filters.audio, temp)
    # dispatcher.add_handler(t)

    updater.start_polling()


if __name__ == '__main__':
    main()

