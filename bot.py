from telebot import types

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    text = m.text.lower()
    
    # --- ЛОГИКА МАРШРУТА С КНОПКАМИ ---
    if any(kw in text for kw in ['маршрут', 'доехать', 'как добраться']):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚗 На машине", callback_data="route_auto"))
        markup.add(types.InlineKeyboardButton("🚂 На поезде", callback_data="route_train"))
        markup.add(types.InlineKeyboardButton("🚉 Электричка", callback_data="route_elec"))
        
        main_route = search_in_knowledge_base("маршрут")
        bot.send_message(m.chat.id, main_route, reply_markup=markup, parse_mode="Markdown")
        return

    # --- ПРИОРИТЕТ 1: Поиск в файле (Контакты, Дома) ---
    file_answer = search_in_knowledge_base(text)
    if file_answer:
        bot.send_message(m.chat.id, file_answer, parse_mode="Markdown")
        return

    # --- ПРИОРИТЕТ 2: База данных (Цены) ---
    # Исправление: если в тексте есть "цена", ищем просто все активные позиции
    search_query = text.replace('цена', '').strip()
    if 'цена' in text and not search_query:
        # Если прислали просто слово "цена", выводим популярное
        search_query = "дом" 

    rows = search_in_db(search_query if search_query else text)
    if rows:
        for r in rows:
            msg = f"🏠 *{r['title']}*\n💰 Цена: {r['price']} руб.\n📞 {r['phone']}\n\n_{r['content'][:250]}_"
            bot.send_message(m.chat.id, msg, parse_mode="Markdown")
        return

    # --- ПРИОРИТЕТ 3: Gemini ---
    # (ваш существующий код Gemini)

# --- ОБРАБОТКА НАЖАТИЙ НА КНОПКИ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('route_'))
def callback_route(call):
    if call.data == "route_auto":
        msg = search_in_knowledge_base("маршрут_авто")
    elif call.data == "route_train":
        msg = search_in_knowledge_base("маршрут_поезд")
    elif call.data == "route_elec":
        msg = search_in_knowledge_base("маршрут_электричка")
    
    if msg:
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")
    bot.answer_callback_query(call.id)
