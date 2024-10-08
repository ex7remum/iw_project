import urllib.request
from bs4 import BeautifulSoup
import pandas as pd
import re
import requests
from deep_translator import GoogleTranslator
from functools import lru_cache
import json 
from openai import OpenAI
import axios
from trie import timeit
from concurrent.futures import ThreadPoolExecutor
import logging
from fireworks.client import Fireworks


class DrugInteractionProcessor:
    def __init__(self):
        # Load the CSV data once and reuse it
        self.drugs_data = pd.read_csv('medicines.csv', sep=';')
        self.drugs_data = self.drugs_data.applymap(lambda s:s.lower() if type(s) == str else s)
    

    @staticmethod
    def translate_deep_translate(text):
        return GoogleTranslator(source='en', target='ru').translate(text)
    

    @staticmethod
    def remove_html_tags(text):
        CLEANR = re.compile('<.*?>')
        cleantext = re.sub(CLEANR, '', text)
        cleantext = re.sub('Therapeutic duplication warnings', 'Therapeutic duplication warnings. ', cleantext)
        return cleantext


    # @timeit
    # def summarize_with_llama(self, openai, text, language='en'):
    #     try:
    #         chat_completion = openai.chat.completions.create(
    #             model="meta-llama/Meta-Llama-3.1-70B-Instruct",
    #             messages=[{"role": "user", "content": f'''Summarize the following text in {language}, use bullet points, start answering with summary,
    #                         write only important information about interactions. Output should be strictly formatted by 5 parts: summary result, danger interaction, medium-risk interaction,
    #                         low-risk, no-risk interaction. First section is about short one-sentence summary of following information like (write to 
    #                        the end of this sentence color in braces like red, yellow and green which represents treat level -- USE ONE WORD WITH symbols like !yellow!): ok treatment or dangerous
    #                         treatment. Don't write about consulting doctors, we will push user to this manually. Also write paragraph named
    #                         duplication shortly. Use $ symbol as separator between every section it's very important to use $ symbol as separator -- ITS REALLY STRICT REQUIREMENT FOR PARSING! After every section name use symbol : it's strictly for parsing!!!:\n{text}'''}],
    #             temperature=0.2,  # Lower value for focused output
    #             n=1,               # Request only one response for faster generation
    #             top_p=1
    #         )
    #         return chat_completion.choices[0].message.content
        
    #     except:
    #         logging.info(f"Error occurred while calling Llama API")
    #         return None


    @timeit
    def summarize_with_llama(self, client, text, language='en'):
        try:
            response = client.chat.completions.create(
                model="accounts/fireworks/models/llama-v3p1-405b-instruct",
                messages=[{
                    "role": "user",
                    "content": f'''Summarize the following text in {language}, use bullet points, start answering with summary. 
Write only important information about interactions. Output should be strictly formatted in 5 parts: 
1. Summary: a one-sentence summary of the information like (write to the end of this sentence 
the color in braces like red, yellow, and green which represents the threat level -- USE ONE WORD WITH 
symbols like !yellow!). 
2. Dangerous Interaction: write about the dangerous interactions. 
3. Medium-Risk Interaction: write about medium-risk interactions. 
4. Low-Risk Interaction: write about low-risk interactions. 
5. No-Risk Interaction: write about interactions with no risk.
6. Duplication: write about duplicative effects of medicines.

Each section should be separated by a $ symbol for parsing. After every section name, use a colon ":" 
for parsing. Duplication section should be short. Do not write about consulting doctors, as this will 
be done manually. USE ONLY {language} LANGUAGE IN RESPONSE, SECTIONS AND COLOR NAMES SHOULD BE IN ENGLISH:\n{text}''',
                }],
            )
            print(response)
            return response.choices[0].message.content
        
        except:
            logging.info(f"Error occurred while calling Llama API")
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
                logging.info(f"Drug {drug} not found.")
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
            logging.info(f"Error occurred: {e}")
            return 'Failed to process drugs'
        

    @timeit
    def parallel_create_proper_responses(self, medicine_list, medicine_list_ids):
        all_info = []
        
        with ThreadPoolExecutor() as executor:
            for i in range(len(medicine_list_ids)):
                for j in range(i, len(medicine_list_ids)):
                    info_from_drugs = self.get_info_from_drugs_com(medicine_list_ids[i], medicine_list_ids[j])
                    
                    # Prepare a list of arguments for parallel processing
                    futures = []
                    for k, info in enumerate(info_from_drugs):
                        if k == 0 or k + 1 == len(info_from_drugs):
                            future = executor.submit(self.create_proper_response, info, medicine_list[i], medicine_list[j])
                        else:
                            future = executor.submit(self.create_proper_response, info, medicine_list[i], 'food')
                        
                        futures.append(future)

                    # Collect the results from each future
                    final_response = ''.join([future.result() for future in futures])
                    
                    all_info.append(final_response)
        
        return all_info
        

    def parse_summary(self, summary):
        try:
            summary = re.sub(r"\*", "", summary)
            summary = re.sub(r"•", "", summary)
            summary = summary.split('$')

            result = {}
            summary = [item for item in summary if item != '']

            # Extract the short answer (first line)
            result['short_answer'] = summary[0]

            for i, item in enumerate(summary):
                if not i:
                    continue
                item = item.strip()
                col_pos = re.search(':', item).start()
                current_section = item[:col_pos] # Remove the colon
                result[item[:col_pos]] = item[col_pos + 1:]
            return result
        except:
            logging.info('Summary in a wrong format')
            return f'Error occurred. Please try later'

            

    def processing(self, client, medicine_list, lang, use_summarizer=False):
        medicine_list = [med.strip() for med in set(medicine_list) if med.strip()]
        medicine_list_ids = self.parse_items_to_ids(medicine_list, lang)

        if len(medicine_list_ids) < 2:
            return "Please choose at least 2 medicines" if lang == 'en' else "Пожалуйста, выберите хотя бы 2 лекарства"
        
        if len(medicine_list_ids) > 4:
            return "Please choose at most 4 drugs. Our resources are limited by now." if lang == 'en' else "Пожалуйста, введите максимум 4 лекарства. Наши ресурсы пока ограничены."

        logging.info('Started getting info')

        try:
            all_info = self.parallel_create_proper_responses(medicine_list, medicine_list_ids)
            logging.info('Ended getting info')
        except:
            logging.info('Error during getting info')
            return "Some error occured. Please, try later" if lang == 'en' else "Произошла ошибка. Попробуйте еще раз"
        

        if lang == 'ru':
            all_info_string = ''
            for eng_info in all_info:
                all_info_string += eng_info + '\n\n'
            
            result_message = f"Вы выбрали следующие лекарства: {', '.join(medicine_list)}\n{all_info_string}"
            if use_summarizer:

                logging.info('Started summarizing')
                summary = self.summarize_with_llama(client, all_info_string, language='ru')
                logging.info('Ended summarizing')

                if summary:
                    result_message = self.parse_summary(summary)
                    logging.info(result_message)
                else:
                    logging.info('Error during summarization in rus')
                    result_message = f'Произошла ошибка. Пожалуйста, попробуйте позже'

            return result_message
        
        result_message = f"You selected the following medicines: {', '.join(medicine_list)}\n{'\n\n'.join(all_info)}"
        if use_summarizer:

            logging.info('Started summarizing')
            summary = self.summarize_with_llama(client, result_message)
            logging.info('Ended summarizing')

            if summary:
                result_message = self.parse_summary(summary)
                logging.info(result_message)
            else:
                logging.info('Error during summarization')
                result_message = f'Error occurred. Please try later'

        return result_message
