import urllib.request
from bs4 import BeautifulSoup
import pandas as pd

def parse_items_to_ids(medicine_list):
    ## TODO: create separate csv file with ids
    drugs_data = pd.read_csv('medicines.csv', sep=';')
    ids = []
    for drug in medicine_list:
        ids.append(drugs_data[drugs_data["Drug_name_en"] == drug]['Id'].iloc[0])
    return ids

def get_info_from_drugs_com(id1, id2):
    url = f'https://www.drugs.com/interactions-check.php?drug_list={id1},{id2}'
    opener = urllib.request.FancyURLopener({})
    f = opener.open(url)
    content = f.read()
    soup = BeautifulSoup(content, 'html.parser')
    info = str(soup)
    ## TODO: parse html
    return info

# Функция обработки списка
def processing(medicine_list, lang):
    medicine_list = list(set(medicine_list))
    medicine_list_ids = parse_items_to_ids(medicine_list)
    ## TODO: Add cycle here. Maybe we should add some timeout(?)
    info = get_info_from_drugs_com(medicine_list_ids[0], medicine_list_ids[1])
    if lang == 'ru':
        return f"Вы выбрали следующие лекарства: {', '.join(medicine_list)}\n {info}"
    else:
        return f"You selected the following medicines: {', '.join(medicine_list)}\n {info}"
        