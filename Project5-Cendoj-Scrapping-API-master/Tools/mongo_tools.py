import os
import re
from datetime import datetime
from os import listdir
from os.path import isfile, join

import numpy as np
import requests
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
from Config.mongo_config import collection

# Ruta global para los archivos PDF
PDF_PATH = r"C:\Users\itzag\PycharmProjects\pythonProject\pdf"

def regex_court_sentence_file():
    """
    Function to regex the folder with the only file, and returns us the data. It deletes the file also.
    :return: dict
    """
    os.makedirs(PDF_PATH, exist_ok=True)
    onlyfiles = [f for f in listdir(PDF_PATH) if isfile(join(PDF_PATH, f))]

    for i in onlyfiles:
        newstr = os.path.join(PDF_PATH, i)
        reader = PdfReader(newstr)
        text = ""

        for page in reader.pages:
            text += page.extract_text() + "\n"

        ## Roj
        roj_match = re.search(r'Roj.*', text)
        if roj_match:
            roj = roj_match.group(0)
            list_roj = roj.split("-")
            roj = list_roj[0].strip()
            ats = roj[9:]
            ecli = list_roj[1].strip()
        else:
            ecli = "couldn't find"
            ats = "Couldn't find"
        print(ats)

        ## cendoj id
        cendoj_match = re.search(r'\d{20}', text)  # type: ignore
        cendoj_id = int(cendoj_match.group(0)) if cendoj_match else 0
        print(cendoj_id)

        ## organo
        organo_match = re.search(r'Órgano.*', text)
        if organo_match:
            organo_total = organo_match.group(0).strip("Órgano:")
            tribunal, sala = organo_total.split(".", 1)
            sala = sala.strip()
        else:
            tribunal = np.nan
            sala = np.nan
        print(tribunal)
        print(sala)

        ## sede
        sede_match = re.search(r'Sede\W.*', text)  # type: ignore
        sede = sede_match.group(0)[6:] if sede_match else "Couldn't find"
        print(sede)

        ## seccion
        seccion_match = re.search(r'Sección\W.*', text)  # type: ignore
        seccion = int(seccion_match.group(0)[9:]) if seccion_match else "Couldn't find"
        print(seccion)

        ## fecha
        fecha_match = re.search(r'Fecha \W\d.*', text)  # type: ignore
        if (fecha_match):
            fecha = fecha_match.group(0)[6:].replace("/", "-", 1)
            fecha = datetime.strptime(fecha, '%d-%m-%y')
        else:
            fecha = np.nan
        print(fecha)

        ## no recurso
        recurso_match = re.search(r'Nº de Rec.*', text)
        recurso_n = recurso_match.group(0)[15:] if recurso_match else "Couldn't find"
        print(recurso_n)

        ## juez
        juez_match = re.search(r'Ponente\W.*', text)  # type: ignore
        juez = juez_match.group(0)[8:] if juez_match else "Couldn't find"
        print(juez)

        ## letrado
        letrado_match = re.search(r'Letrado\W.*', text)  # type: ignore
        letrado = letrado_match.group(0).removeprefix('Letrado de la Administración de Justicia: Ilmo. Sr. D. ') if letrado_match else "Couldn't find"
        print(letrado)

        # Remove file
        if os.path.isfile(newstr):
            os.remove(newstr)
        else:
            print(f"Error: {newstr} file not found")

        data_sentence = {
            "ATS": ats,
            "ECLI": ecli,
            "Cendoj_id": cendoj_id,
            "Tribunal": tribunal,
            "Sala": sala,
            "Sede": sede,
            "Seccion": seccion,
            "Fecha": fecha,
            "Numero_recurso": recurso_n,
            "Juez": juez,
            "Letrado": letrado,
            "Full_text": text
        }

        print(data_sentence)
        return data_sentence

def uploading_mongo(data_sentence):
    try:
        collection.insert_one(data_sentence)
        print("Data inserted successfully into MongoDB")
    except Exception as e:
        print(f"An error occurred: {e}")

def downloading_sentence(url):
    """
    This function takes an url of a CENDOJ sentence, downloads it, and saves it.
    :param url: string, url of the CENDOJ sentence
    :return: None
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    href = soup.find("object", {"id": "objtcontentpdf"})
    href = href.find("a", href=True)  # type: ignore
    href = "https://www.poderjudicial.es" + href["href"]  # type: ignore

    PARAMS = {'address': PDF_PATH}

    i = requests.get(url=href, params=PARAMS)

    with open(os.path.join(PDF_PATH, 'sentence.pdf'), 'wb') as f:
        f.write(i.content)

    m = re.search(r'\d{8}', href)  # type: ignore
    if m:
        name_file = m.group(0) + ".pdf"
    else:
        name_file = "sentence.pdf"

    onlyfiles = [f for f in listdir(PDF_PATH) if isfile(join(PDF_PATH, f))]
    if onlyfiles:
        file = onlyfiles[0]
        old_file = os.path.join(PDF_PATH, file)
        new_file = os.path.join(PDF_PATH, name_file)
        os.rename(old_file, new_file)

def get_all_from_mongo():
    results = collection.find({}, {"_id": 0, "ATS": 1, "ECLI": 1, "Cendoj_id": 1, "Tribunal": 1, "Sala": 1, "Sede": 1, "Seccion": 1, "Fecha": 1, "Numero_recurso": 1, "Juez": 1, "Letrado": 1})
    return list(results)

def get_count_with_variable(variable):
    pipeline = [
        {"$group": {"_id": f"${variable}", "Sentencias_Totales": {"$sum": 1}}},
        {"$sort": {"Sentencias_Totales": -1}}
    ]
    results = collection.aggregate(pipeline)
    return list(results)

def get_all_with_variable(variable, name):
    query = {variable: name}
    results = collection.find(query).sort("Fecha", -1)
    return list(results)

def return_last_mongo():
    results = collection.find().sort("_id", -1).limit(1)
    return list(results)
