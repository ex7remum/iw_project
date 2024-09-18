from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session
from processing import DrugInteractionProcessor
import pandas as pd
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

def download_csv():
    if not os.path.exists('medicines.csv'):
        url = "https://docs.google.com/spreadsheets/d/1NmeYrISaCTMogoEGRXgL8A7hvcfgfB8hQ_PG4gYPKcM/export?format=csv"
        df = pd.read_csv(url, index_col=0)
        df.to_csv(path_or_buf='medicines.csv', sep=';', index=True)

download_csv()
processor = DrugInteractionProcessor()  # Instantiate the processor once


# Function to load medicines from CSV
def load_medicines(lang):
    # Check if the CSV file exists or download it
    download_csv()

    drugs_data = pd.read_csv('medicines.csv', sep=';')
    if lang == 'ru':
        return drugs_data['Drug_name_rus'].values.tolist()
    return drugs_data['Drug_name_en'].values.tolist()

# Start page
@app.route('/', methods=['GET', 'POST'])
def index():
    # Set default language
    if 'lang' not in session:
        session['lang'] = 'ru'

    medicines = load_medicines(session['lang'])
    result = ''

    if request.method == 'POST':
        if 'lang_switch' in request.form:
            # Language switch handling
            session['lang'] = 'ru' if session['lang'] == 'en' else 'en'
            return redirect(url_for('index'))
        else:
            # Input processing
            medicines_input = request.form.get('medicines').split(',')
            valid_medicines = [med.strip() for med in medicines_input if med.strip() in medicines]
            result = processor.processing(valid_medicines, session['lang'])

    return render_template('index.html', result=result, lang=session['lang'])

# Autocomplete route
@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('q', '')
    medicines = load_medicines(session['lang'])
    suggestions = [med for med in medicines if query.lower() in med.lower()]
    return jsonify(suggestions)


if __name__ == '__main__':
    app.run(debug=False)
