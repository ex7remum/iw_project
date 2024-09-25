import urllib.request
from bs4 import BeautifulSoup
import pandas as pd
import re
import requests
from deep_translator import GoogleTranslator
from functools import lru_cache
import json 
from openai import OpenAI
import axios  # Make sure to install this: pip install axios
#pip install lxml before works

class DrugInteractionProcessor:
    def __init__(self):
        # Load the CSV data once and reuse it
        self.drugs_data = pd.read_csv('medicines.csv', sep=';')
        self.drugs_data= self.drugs_data.applymap(lambda s:s.lower() if type(s) == str else s)
    

    @staticmethod
    def translate_deep_translate(text):
        return GoogleTranslator(source='en', target='ru').translate(text)
    

    @staticmethod
    def remove_html_tags(text):
        CLEANR = re.compile('<.*?>')
        cleantext = re.sub(CLEANR, '', text)
        cleantext = re.sub('Therapeutic duplication warnings', 'Therapeutic duplication warnings. ', cleantext)
        return cleantext


    def summarize_with_llama(self, openai, text, language='en'):
        try:
            chat_completion = openai.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-405B-Instruct",
                messages=[{"role": "user", "content": f"Summarize the following text in {language}, use bullet points, start answering with summary, write only important information about interactions. Split information by 4 parts: danger interaction, medium-risk interaction, low-risk, no-risk interaction. Write at the top one short sentence which summarize all of following information like (write to the end of this sentence color in braces like red, yellow and green which represents treat level): ok treatment or dangerous treatment and so on. Don't write about consulting doctors, we will push user to this manually. Also write paragraph named duplication shortly:\n{text}"}],
            )
            return chat_completion.choices[0].message.content
        
        except requests.RequestException as e:
            print(f"Error occurred while calling Llama API: {e}")
            return None
    

    def parse_items_to_ids(self, medicine_list, lang):
        ids = []
        for drug in medicine_list:
            try:
                if lang == 'en':
                    ids.append(self.drugs_data[self.drugs_data["Drug_name_en"] == drug]['Id'].iloc[0])
                else:
                    ids.append(self.drugs_data[self.drugs_data["Drug_name_rus"] == drug]['Id'].iloc[0])
            except IndexError:
                print(f"Drug {drug} not found.")
        return ids
    

    @staticmethod
    def create_proper_response(response, drug1, drug2):
        res_response = ''
        if 'Applies to' in response:
            while 'Applies to:' in response:
                start_pos = re.search(r'Applies to:', response).start()
                response = response[start_pos:]

                cur_response = re.split('Major', response)[0]
                start_pos = re.search('[A-Z]', cur_response[1:]).start()

                res_response += f'{cur_response[:start_pos + 1]}: {cur_response[(start_pos + 1):]}\n\n'
                response = response[start_pos + 1:]

            res_response = re.sub('Switch to professional interaction data', '', res_response)
            return res_response
        else:
            return f'{drug1} and {drug2}: {response}\n\n'


    def get_info_from_drugs_com(self, id1, id2):
        try:
            url = f'https://www.drugs.com/interactions-check.php?drug_list={id1},{id2}'
            response = requests.get(url)
            response.raise_for_status()  # Raise an error for bad responses

            soup = BeautifulSoup(response.content, 'lxml')  # Use lxml for faster parsing
            interactions_list_info = soup.find_all('div', {"class": "interactions-reference-wrapper"})

            # Remove all inside <>
            info = [self.remove_html_tags(str(interaction_info)) for interaction_info in interactions_list_info]

            return info
        except requests.RequestException as e:  # Handle request exceptions
            print(f"Error occurred: {e}")
            return ['Failed to process drugs']
            

    def processing(self, openai, medicine_list, lang, use_summarizer=False):
        medicine_list = [med.strip() for med in set(medicine_list) if med.strip()]
        medicine_list_ids = self.parse_items_to_ids(medicine_list, lang)

        all_info = []
        if len(medicine_list_ids) < 2:
            return "please choose at least 2 medicines"

        for i in range(len(medicine_list_ids)):
            for j in range(i, len(medicine_list_ids)):
                info_from_drugs = self.get_info_from_drugs_com(medicine_list_ids[i], medicine_list_ids[j])
                final_response = ''
                for k, info in enumerate(info_from_drugs):
                    if k == 0 or k + 1 == len(info_from_drugs):
                        response = self.create_proper_response(info, medicine_list[i], medicine_list[j])
                    else:
                        response = self.create_proper_response(info, medicine_list[i], 'food')
                    final_response += response
                all_info.append(final_response)

        if lang == 'ru':
            all_info_string = ''
            for eng_info in all_info:
                #translated_info = self.translate_deep_translate(eng_info)
                all_info_string += eng_info + '\n\n'
            
            result_message = f"Вы выбрали следующие лекарства: {', '.join(medicine_list)}\n{all_info_string}"
            if use_summarizer:
                summary = self.summarize_with_llama(openai, all_info_string, language='ru')
                if summary:
                    result_message = summary
                else:
                    result_message = f'Произошла ошибка. Пожалуйста, попробуйте позже'

            return result_message
        
        result_message = f"You selected the following medicines: {', '.join(medicine_list)}\n{'\n\n'.join(all_info)}"
        if use_summarizer:
            summary = self.summarize_with_llama(openai, result_message)
            if summary:
                result_message = summary
            else:
                result_message = f'Error occurred. Please try later'

        return result_message
