# coding: utf-8
from multiprocessing import process

import os
import logging
import xml.etree.ElementTree as ET
from django.utils import timezone
import pytz
from django.template import loader
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives
from django.conf import settings
from pathlib import Path
from concurrent.futures.thread import ThreadPoolExecutor
from itertools import product
import multiprocessing
from math import *
from django import db


from ..models import Process, Error
from .alma_to_sudoc import exist_in_sudoc
from .sudoc_to_alma import exist_in_alma
from .alma_apis import exist_in_alma_via_api

#Initialisation des logs
logger = logging.getLogger(__name__)

class MainProcess(object):
    def __init__(self, datas, process):
        self.datas = datas
        self.process = process
        logger.debug("{}".format(self.process.process_job_type))

    def run(self) :
        num_line = Error.objects.filter(error_process=self.process,error_type='PPN_MAL_FORMATE').count()
        if self.process.process_job_type == 'SUDOC_TO_ALMA':
            ids = [0, 1, 2, 3,4,5]
            manager = multiprocessing.Manager()
            idQueue = manager.Queue()
            for i in ids:
                idQueue.put(i)
            db.connections.close_all()
            p = multiprocessing.Pool(8, self.init, (idQueue,))
            for result in p.imap(self.thread, self.datas):
                num_line += 1
                logger.info(result)
                ppn, (error_code, error_message) = result
                logger.info("{}:{}:{}:{}\n".format(num_line,ppn, error_code,error_message))
                if error_code != 'OK' :
                    # Appel de l'api get records. Le SRU retourne parfois des erreurs ou 0 résulats pour des notices dont les localisations 
                    # ont été masquées par la découverte. Dans ce cas on appelle le web service get
                    if error_code in ('PPN_INCONNU_ALMA','ERREUR_REQUETE') :
                        error_code, error_message = exist_in_alma_via_api(ppn, self.process)
                        logger.debug(error_code)
                        if error_code != 'OK' :
                            error = Error(  error_ppn = ppn,
                                error_type = error_code,
                                error_message = error_message,
                                error_process = self.process)
                            error.save()
                    else :     
                        error = Error(  error_ppn = ppn,
                            error_type = error_code,
                            error_message = error_message,
                            error_process = self.process)
                        error.save()
                # Tous les 100 ppn traités on met à jour le compteur des nbs de titres
                if num_line%100 == 0 :
                    self.save_process(num_line)
            logger.info("Tous les Threads sont termines  !!!")
            logger.debug("{}".format(settings.ADMINS[0][1]))
        else :
            for ppns in self.datas :
                exist_in_sudoc(ppns,self.process)
                num_line += len(ppns)
                self.save_process(num_line)
        self.save_process(num_line,True)
        
        plain_message = loader.render_to_string("sudoc_recouv/end_process_message.txt", locals())
        user_email = EmailMessage(
            "L'analyse de recouvrement est terminée",
            plain_message,
            settings.ADMINS[0][1],
            [self.process.process_user.email],
        )
        user_email.send(fail_silently=False)
        logger.debug("mail envoye !!!")


    def init(self,queue):
        global idx
        idx = queue.get()

    def thread(self,ppn):
        global idx
        return exist_in_alma(ppn, self.process)

    def save_process(self, num_line, is_done = False) :
        self.process.process_is_done = is_done
        self.process.process_num_title_processed = num_line
        self.process.process_end_date = timezone.now()
        self.process.process_num_ppn_mal_formate = Error.objects.filter(error_process=self.process,error_type='PPN_MAL_FORMATE').count()
        self.process.process_num_ppn_inconnus_alma = Error.objects.filter(error_process=self.process,error_type='PPN_INCONNU_ALMA').count()
        self.process.process_num_ppn_inconnus_sudoc = Error.objects.filter(error_process=self.process,error_type='PPN_INCONNU_SUDOC').count()
        self.process.process_num_loc_inconnues_alma = Error.objects.filter(error_process=self.process,error_type='LOC_INCONNUE_ALMA').count()
        self.process.process_num_loc_inconnues_sudoc = Error.objects.filter(error_process=self.process,error_type='LOC_INCONNUE_SUDOC').count()
        self.process.process_num_doublons_notices_alma = Error.objects.filter(error_process=self.process,error_type='DOUBLON_ALMA').count()
        self.process.process_num_erreurs_requetes = Error.objects.filter(error_process=self.process,error_type='ERREUR_REQUETE').count()
        self.process.save()