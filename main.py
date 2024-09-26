from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session

from fireworks.client import Fireworks
from processing import DrugInteractionProcessor
from trie import Trie
import pandas as pd
import os
from trie import TrieVisualizer
from scout_apm.flask import ScoutApm
import argparse
from openai import OpenAI
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)


def download_csv():
    url = "https://docs.google.com/spreadsheets/d/1NmeYrISaCTMogoEGRXgL8A7hvcfgfB8hQ_PG4gYPKcM/export?format=csv"

    # Load the remote CSV file
    remote_df = pd.read_csv(url, index_col=0)

    # Check if the local CSV file exists
    if os.path.exists('medicines.csv'):
        # Load the local CSV file
        local_df = pd.read_csv('medicines.csv', sep=';', index_col=0)
        
        # Check if the local and remote CSV files are the same
        if not local_df.equals(remote_df):
            print("Local file is outdated. Updating the file...")
            # Update the local CSV file if the content differs
            remote_df.to_csv('medicines.csv', sep=';', index=True)
        else:
            print("Local file is up to date.")
    else:
        print("Local file does not exist. Downloading the file...")
        # If the local file doesn't exist, save the remote file
        remote_df.to_csv('medicines.csv', sep=';', index=True)


download_csv()
logger = logging.getLogger(__name__)

processor = DrugInteractionProcessor()  # Instantiate the processor once
use_summ_flag = True
#openai = OpenAI(
#    api_key="iDBzr5fb4hdSxT3iNcrqoFfihjZ7PK9D",
#    base_url="https://llama3-1-70b.lepton.run/api/v1/",
#)

client = Fireworks(api_key="fw_3ZMX9uLmrm2PNJyAuCVPypHc")


# Function to load medicines from CSV
def load_medicines(lang):
    # Check if the CSV file exists or download it
    download_csv()

    drugs_data = pd.read_csv('medicines.csv', sep=';')
    if lang == 'ru':
        return list(map(lambda x: x.lower(), drugs_data['Drug_name_rus'].values.tolist()))
    return list(map(lambda x: x.lower(), drugs_data['Drug_name_en'].values.tolist()))


# Start page
@app.route('/', methods=['GET', 'POST'])
def index():
    # Set default language
    if 'lang' not in session:
        session['lang'] = 'en'
    #medicine_trie = Trie(session['lang'])  # this causes the session error
    
    medicines = load_medicines(session['lang'])
    
    result = ''
    if request.method == 'POST':
        if 'lang_switch' in request.form:
            # Language switch handling
            session['lang'] = 'ru' if session['lang'] == 'en' else 'en'
            return redirect(url_for('index'))
        else:
            # Input processing
            medicines_input = list(map(lambda x: x.strip().lower(), request.form.get('medicines').split(',')))

            valid_medicines = [med.strip().lower() for med in medicines_input if med.strip() in medicines]
           
            result = processor.processing(client, valid_medicines, session['lang'], use_summarizer=use_summ_flag)

    return render_template('index.html', result=result, lang=session['lang'])


# Autocomplete route
@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])

    if 'lang' not in session:
        session['lang'] = 'en'
        
    medicine_trie = Trie(session['lang'])
    
    # Get autocomplete suggestions from the trie
    suggestions = medicine_trie.autocomplete(query)
    
    if not suggestions:
        return jsonify([f"No medicines found starting with '{query}'"])
    
    suggestions = list(map(str.strip, list(map(str.capitalize, suggestions))))
    return jsonify(suggestions)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='DocMeds',
                    description='Check drug interaction')
    parser.add_argument('-u', '--use_summ', default='yes')
    args = parser.parse_args()
    logging.basicConfig(filename='myapp.log', level=logging.INFO)

    if args.use_summ == 'no':
        use_summ_flag = False
    else:
        use_summ_flag = True

    app.run(host='0.0.0.0', port=5000, debug=True)