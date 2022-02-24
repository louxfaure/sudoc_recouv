# coding: utf-8
import re
import os
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import xml.etree.ElementTree as ET
import time

from django.conf import settings

from ..models import Process, Error

#Initialisation des logs
logger = logging.getLogger(__name__)

def test_localisation(librairies,rcr):
    for library in librairies:
        if rcr == library.attrib['rcr'] :
            return True
    return False

def request_in_sudoc(ppns_list,process):
    """Teste pour une liste de PPN et un RCR donnés si une localisation existe dans le SUDOC

    Args:
        ppns_list (array): liste de ppn
        process (objec): traitement pour lequel la liste doit être traitée conctient le rcr process.process_library.library_rcr
    """
 
    # Préparation et envoie de la requête à l'ABES
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    r = session.request(
        method='GET',
        headers= {
            "User-Agent": "outils_biblio/0.1.0",
            "Accept": "application/xml"
        },
        url= 'https://www.sudoc.fr/services/where/15/{}.xml'.format(','.join(ppns_list)))
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        logger.error("{} :: alma_to_sudoc :: HTTP Status: {} || Method: {} || URL: {} || Response: {}".format(','.join(ppns_list), r.status_code, r.request.method, r.url, r.text))
        # Si le service ne répond pas pour la requête on créé une erreur pour chaque PPN
        for ppn in ppns_list :
            error = Error(  error_ppn = ppn,
                    error_type = 'ERREUR_REQUETE',
                    error_process = process,
                    error_message = r.text)        
            error.save() 
        return False, "ERREUR_REQUETE"
    # Si pas de soucis on retourne les résultats    
    else:
        results = r.content.decode('utf-8')
        return True, results


def exist_in_sudoc(ppns_list,process):
    """Teste pour une liste de PPN et un RCR données si une localisation existe dans le SUDOC

    Args:
        ppns_list (array): liste de ppn
        process (object): traitement pour lequel la liste doit être traitée contient le rcr process.process_library.library_rcr
    """
    rcr = process.process_library.library_rcr
    logger.info("Thread {} début".format(ppns_list))

    # On interroge le SUDOC
    statut, results = request_in_sudoc(ppns_list,process)
    if statut :
        ppns_connus =[] #Liste des ppns retrouvés par le web service
        root = ET.fromstring(results)
        #Pour chaque résultat 
        for result in root.findall(".//result"):
            # On récupère le PPN
            ppn = result.attrib['ppn']
            # On l'ajoute à la liste des ppns retrouvés par le web service
            ppns_connus.append(ppn)
            # On regarde si une localisation existe pour le RCR 
            is_located = test_localisation(result.findall(".//library"),rcr)
            if is_located :
                logger.debug("{} :: Existe".format(ppn))
            else :
                error = Error(  error_ppn = ppn,
                    error_type = 'LOC_INCONNUE_SUDOC',
                    error_process = process)
                error.save()
                logger.debug("{} :: Localisation inconnue du SUDOC".format(ppn))
        # On identifie les ppns inconnus du SUDOC
        for ppn in ppns_list :
            if ppn not in ppns_connus :
                error = Error(  error_ppn = ppn,
                    error_type = 'PPN_INCONNU_SUDOC',
                    error_process = process)
                error.save()
                logger.debug("{} :: PPN inconnu du SUDOC".format(ppn))

