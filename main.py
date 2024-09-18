from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session

from processing import processing

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Чтение файлов с лекарствами
def load_medicines(lang):
    if lang == 'ru':
        with open('medicines_ru.txt', encoding='utf-8') as f:
            return [line.strip() for line in f.readlines()]
    else:
        with open('medicines_en.txt', encoding='utf-8') as f:
            return [line.strip() for line in f.readlines()]

# Стартовая страница
@app.route('/', methods=['GET', 'POST'])
def index():
    # Установим язык по умолчанию
    if 'lang' not in session:
        session['lang'] = 'ru'

    medicines = load_medicines(session['lang'])
    result = ''

    if request.method == 'POST':
        if 'lang_switch' in request.form:
            # Обработка смены языка
            session['lang'] = 'ru' if session['lang'] == 'en' else 'en'
            return redirect(url_for('index'))
        else:
            # Обработка введенных данных
            medicines_input = request.form.get('medicines').split(',')
            valid_medicines = [med.strip() for med in medicines_input if med.strip() in medicines]
            result = processing(valid_medicines, session['lang'])

    return render_template('index.html', result=result, lang=session['lang'])

# Маршрут для автозаполнения
@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('q', '')
    medicines = load_medicines(session['lang'])
    suggestions = [med for med in medicines if query.lower() in med.lower()]
    return jsonify(suggestions)

if __name__ == '__main__':
    app.run(debug=True)
