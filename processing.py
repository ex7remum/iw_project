import urllib.request
from bs4 import BeautifulSoup
import pandas as pd
import re
import requests
from deep_translator import GoogleTranslator


def translate_yandex(text):
    IAM_TOKEN = 't1.9euelZqKjpWbj4yej5eXi5HKm5iZyO3rnpWam4qUzZCdl5iXk4qUysrKkJXl8_caYVVI-e8zcXAm_N3z91oPU0j57zNxcCb8zef1656VmpeTk8mVnY7Nls6exp7JzMyO7_zF656VmpeTk8mVnY7Nls6exp7JzMyO.2fhOg3G_vwU8c-BVB9pqe1BHSvxIt3YuxGgRh8QXfli-vm-IscOyKyiLCRl4sDxAL4FEhLBIcKSnG8bCz_RMBQ'
    folder_id = 'b1gjl3igfd6hqo8im7uc'
    target_language = 'ru'
    texts = [text]

    body = {
        "targetLanguageCode": target_language,
        "texts": texts,
        "folderId": folder_id,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {0}".format(IAM_TOKEN)
    }

    response = requests.post('https://translate.api.cloud.yandex.net/translate/v2/translate',
        json = body,
        headers = headers
    )

    return response.text


def translate_deep_translate(text):
    return GoogleTranslator(source='en', target='ru').translate(text)


def remove_html_tags(text):
    CLEANR = re.compile('<.*?>')
    cleantext = re.sub(CLEANR, '', text)
    cleantext = re.sub('Therapeutic duplication warnings', 'Therapeutic duplication warnings. ', cleantext)
    return cleantext


def parse_items_to_ids(medicine_list, lang):
    drugs_data = pd.read_csv('medicines.csv', sep=';')
    ids = []
    # print(medicine_list, lang)
    for drug in medicine_list:
        if lang == 'en':
            ids.append(drugs_data[drugs_data["Drug_name_en"] == drug]['Id'].iloc[0])
        else:
            ids.append(drugs_data[drugs_data["Drug_name_rus"] == drug]['Id'].iloc[0])
    return ids


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
        return f'{drug1} and {drug2}: {response}'


def get_info_from_drugs_com(id1, id2):
    url = f'https://www.drugs.com/interactions-check.php?drug_list={id1},{id2}'
    opener = urllib.request.FancyURLopener({})
    f = opener.open(url)
    content = f.read()
    soup = BeautifulSoup(content, 'html.parser')

    interactions_list_info = soup.find_all('div', {"class": "interactions-reference-wrapper"})

    ## remove all inside <>
    info = []
    for interaction_info in interactions_list_info:
        info.append(remove_html_tags(str(interaction_info)))

    return info


# Функция обработки списка
def processing(medicine_list, lang):

    medicine_list = list(set(medicine_list))
    medicine_list_ids = parse_items_to_ids(medicine_list, lang)

    ## TODO: Maybe we should add some timeout(?)
    all_info = []
    for i in range(len(medicine_list_ids)):
        for j in range(i, len(medicine_list_ids)):
            info_from_drugs = get_info_from_drugs_com(medicine_list_ids[i], medicine_list_ids[j])
            final_response = ''
            for k, info in enumerate(info_from_drugs):
                if k == 0 or k + 1 == len(info_from_drugs):
                    response = create_proper_response(info, medicine_list[i], medicine_list[j])
                else:
                    response = create_proper_response(info, medicine_list[i], 'food')
                final_response += response
            all_info.append(final_response)

    if lang == 'ru':
        all_info_string = ''
        for i, eng_info in enumerate(all_info):
            print(f'iter: {i}')
            translated_info = translate_deep_translate(eng_info)
            all_info_string += translated_info + '\n\n'
        return f"Вы выбрали следующие лекарства: {', '.join(medicine_list)}\n{all_info_string}"
    
    else:
        return f"You selected the following medicines: {', '.join(medicine_list)}\n{'\n\n'.join(all_info)}"
