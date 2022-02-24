# -*- coding: utf-8 -*-
import os
# external imports
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry 
import json
import logging
import xml.etree.ElementTree as ET
import time
import sys
from django.conf import settings
from ..models import Library

#Initialisation des logs
logger = logging.getLogger(__name__)

__version__ = '0.1.0'
__api_version__ = 'v1'
__apikey__ = os.getenv('ALMA_API_KEY')
__region__ = os.getenv('ALMA_API_REGION')

NS = {'sru': 'http://www.loc.gov/zing/srw/',
        'marc': 'http://www.loc.gov/MARC21/slim',
        'xmlb' : 'http://com/exlibris/urm/general/xmlbeans'
         }

def get_error_message(response):
        """Extract error code & error message of an API response
        
        Arguments:
            response {object} -- API REsponse
        
        Returns:
            int -- error code
            str -- error message
        """
        error_code, error_message = '',''
        root = ET.fromstring(response.text)
        error_message = root.find(".//xmlb:errorMessage",NS).text if root.find(".//xmlb:errorMessage",NS).text else response.text 
        error_code = root.find(".//xmlb:errorCode",NS).text if root.find(".//xmlb:errorCode",NS).text else '???'
    
        return error_code, error_message

def test_localisation(ppn, record,library_id):
    logger.debug("test_loc pour {}".format(ppn))
    root = ET.fromstring(record)
   
    # On teste le nombre de résultat
    nb_result = root.attrib['total_record_count']
    logger.debug(nb_result)
    if int(nb_result) == 0 :
        return "PPN_INCONNU_ALMA","L'API get records ne remonte aucun résultat pour le ppn"
    elif int(nb_result) > 1 :
        return "DOUBLON_ALMA", "L'API get records remonte plusieurs résultats pour le même ppn"
    else :
        # On va regarder si la bibliothèque est bien localisée. On parcourt les champs AVA
        for dispo in root.findall(".//datafield[@tag='AVA']"):
            logger.debug(dispo.find("subfield[@code='q']").text)
            if dispo.find("subfield[@code='b']").text in library_id :
                return "OK", "Le document est bien localisé dans Alma"
        return "LOC_INCONNUE_ALMA", "Aucune localisation existe sous la notice pour la bibliothèque (Apis Get Records)"    

    logger.debug(root[1].tag)

def exist_in_alma_via_api(ppn,process):
    api_key = settings.ALMA_API_KEY[process.process_library.institution]
    logger.debug(os.getenv("PROD_UBM_API"))
    library_id = Library.objects.filter(library_rcr = process.process_library.library_rcr).values_list('library_id', flat=True)
    library_id = list(library_id)
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    url = "https://api-eu.hosted.exlibrisgroup.com/almaws/v1/bibs?view=full&expand=p_avail&other_system_id=(PPN){}".format(ppn)
    logger.debug(url)
    r = session.request(
        method='GET',
        headers= {
            "User-Agent": "scoop_util/0.1.0",
            "Authorization": "apikey {}".format(api_key),
            "Accept": "application/xml"
        },
        url= url)
    try:
        r.raise_for_status()  
    except :
        error_code, error_msg = get_error_message(r)
        logger.error("{} :: sudoc_to_sudoc :: HTTP Status: {} || Method: {} || URL: {} || Response: {} : {}".format(
                                            ppn,
                                            r.status_code,
                                            r.request.method,
                                            r.url,
                                            error_code,
                                            error_msg))
        return "ERREUR_REQUETE","{} : {}".format(error_code,error_msg)
    logger.debug(r.content.decode('utf-8'))
    return test_localisation(ppn, r.content.decode('utf-8'),library_id)