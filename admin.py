from math import ceil
from django.contrib import admin
from django.http import HttpResponse,HttpResponseRedirect
from django.urls import path
from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings
from .models import Library, Process, Error
from .forms import UploadFileForm
from .services import main,Alma_Sets
import csv
import logging
import threading
import re
import json
# Register your models here.

#Initialisation des logs
logger = logging.getLogger(__name__)

def chunks(lst, n):
    """Tronçonne une liste en listes de n éléments 

    Args:
        lst (array): liste à tronçonner
        n (int): taille des sous-ensembles

    Yields:
        array : liste de listes
    """

    for i in range(0, len(lst), n):
        yield lst[i:i + n]

#Thread pour le lancement du traitement
class ExecuteJobThread(threading.Thread):

    def __init__(self,alma_to_sudoc_anomalies,sudoc_to_alma_anomalies,process):
        self.alma_to_sudoc_anomalies = alma_to_sudoc_anomalies
        self.sudoc_to_alma_anomalies = sudoc_to_alma_anomalies
        self.process = process
        threading.Thread.__init__(self)

    def run(self):
        logger.debug("Lancement du traitement ExecuteJobThread")
        handle_uploaded_file = main.MainProcess(self.alma_to_sudoc_anomalies,self.sudoc_to_alma_anomalies,self.process)
        handle_uploaded_file.run()
        logger.debug("Ending ExecuteJobThread")

# EXport en CSV
class ModesExport:
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        first_result = queryset.first()
        file_name = "{}_{}".format(first_result.error_process.process_library.library_name,first_result.error_type)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(file_name)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Exporter en CSV"

    def export_libraries_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]
        first_result = queryset.first()
        file_name = "{}_{}_{}".format(first_result.library_name,first_result.library_id,first_result.library_rcr,first_result.institution)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(file_name)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Exporter en CSV"

    def export_as_set(self, request, queryset):
        #Permet de faire un set avec les notices en erreur 
        first_result = queryset.first()
        # if first_result.error_process.process_job_type == 'SUDOC_TO_ALMA' :
        #     messages.error(request, "La création des jeux de résultat n'est pas disponible pour les anomalies issues du recouvrement Sudoc vers Alma. Utilisez l'export CSV.")
        #     return HttpResponseRedirect(request.path_info)  
        set_name = "{}_{}".format(first_result.error_process,first_result.error_type)     
        apikey=settings.ALMA_API_KEY[first_result.error_process.process_library.institution]
        #On créé un set que l'on va ensuite alimenter. On e peut créeer dire'ctement un set alimenté avec des PPNS 
        api_set = Alma_Sets.Set(apikey=apikey)
        error,reponse = api_set.create_set(set_name)
        logger.debug(reponse)
        # error = False
        if error :
            messages.error(request,"Le jeux de résultat n'a pas pu être créé. {}".format(reponse))
        else : 
            logger.debug(ceil(queryset.count()/2))
        # On va ajouter nos PPNS dans le set =. On est limité à 1000 ppn par envoi
            nb_ligne = 0
            members_list = []
            for obj in queryset:
                nb_ligne += 1
                members_list.append({"id" : "(PPN){}".format(obj.error_ppn)})
                logger.debug(obj.error_ppn)
                if nb_ligne%999== 0 :
                    error,reponse = api_set.update_set(reponse,members_list,set_name)
                    members_list = []
                    if error :
                        messages.error(request,"Le jeux de résultat n'a pas pu être créé. {}".format(reponse))
                        break    
            if len(members_list) > 0 :     
                error,reponse = api_set.update_set(reponse,members_list,set_name)
                if error :
                    messages.error(request,"Le jeux de résultat n'a pas pu être créé. {}".format(reponse))
                else :
                    messages.success(request, 'Le set {} a été créé avec succès'.format(set_name))

    export_as_set.short_description = "Créer un jeu de résultat Alma"


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin,ModesExport):
    list_display = ('library_id', 'library_rcr', 'library_name', 'institution')
    ordering = ('library_name', 'institution')
    search_fields = ('library_id', 'library_rcr', 'library_name')
    actions = ["export_libraries_as_csv"]

@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('process_library',
                    'process_is_done', 
                    'process_start_date',
                    'process_end_date',
                    'process_num_title_to_processed', 
                    'process_num_title_processed',
                    'link_process_num_ppn_mal_formate',
                    'link_process_num_ppn_inconnus_alma',
                    'link_process_num_loc_inconnues_alma',
                    'link_process_num_ppn_inconnus_sudoc',
                    'link_process_num_loc_inconnues_sudoc',
                    'link_process_num_doublons_notices_alma',
                    'link_process_num_erreurs_requetes')
    ordering = ('-process_start_date', 'process_library')
    list_filter = ['process_library','process_start_date']
    search_fields = ('process_library', 'process_start_date','process_is_done','id')
    form = UploadFileForm
    
    # Ajoute un bloc dédié au messade utilisateur
    def render_change_form(self, request, context, *args, **kwargs):
        # here we define a custom template
        self.change_form_template = 'sudoc_recouv/message_aide.html'
        extra = {
            'help_text': "This is a help message. Good luck filling out the form."
        }

        context.update(extra)
        return super(ProcessAdmin, self).render_change_form(request,
            context, *args, **kwargs)

    # Empêche le message standart d'enregistrement d'un modèle à l'execution d'un traitement
    def message_user(self, request, message, level=messages.INFO, extra_tags='',
                 fail_silently=False):
        pass

    def nettoyage_des_fichiers(self,liste, obj,error_msg):
        out_list = []
        for line in liste :
            line = line.rstrip()
            clean_ppn = re.search("(^|\(PPN\))([0-9]{8}[0-9Xx]{1})(;|$)", line.decode())
            if clean_ppn  is None :
                logger.debug("{} - N'est pas un PPN valide ".format(line.decode()))
                error = Error(  error_ppn = line.decode(),
                        error_type = 'PPN_MAL_FORMATE',
                        error_process = obj,
                        error_message = error_msg)
                error.save()
            else :
                out_list.append(clean_ppn.group(2))
        return set(out_list)


    def save_model(self, request, obj, form, change):
        user = request.user
        form.save(commit=False)
        obj.process_user = user
        obj.process_num_title_to_processed = 0
        obj.save()        
        logger.info("Process cree")
        liste_alma = self.nettoyage_des_fichiers(request.FILES['file_alma'],obj,'Export Alma')
        liste_sudoc = self.nettoyage_des_fichiers(request.FILES['file_sudoc'],obj,'Export SUDOC')           
        alma_to_sudoc_anomalies = list(liste_alma - liste_sudoc)
        sudoc_to_alma_anomalies = list(liste_sudoc - liste_alma)
        obj.process_num_title_processed = len(list(liste_alma.intersection(liste_sudoc)))
        obj.process_num_title_to_processed = obj.process_num_title_processed + len(sudoc_to_alma_anomalies) + len(alma_to_sudoc_anomalies)
        logger.debug(obj)
        obj.save()    
        logger.debug(alma_to_sudoc_anomalies)
        obj.process_num_ppn_mal_formate = Error.objects.filter(error_process=obj,error_type='PPN_MAL_FORMATE').count()
        obj.save()
        # Pour l'analyse de recouvrement Alma vers le SUDOC on requête le service de l'abes par lot de 50 PPN 
        
        alma_to_sudoc_anomalies = list(chunks(alma_to_sudoc_anomalies,50))
        #Lancement de l'analyse de recouvrement
        ExecuteJobThread(alma_to_sudoc_anomalies,sudoc_to_alma_anomalies,obj).start()
        request.session['pid'] = obj.id
        messages.success(request, 'L''analyse de recouvrement a été lancée pour la bibliothèque {}. Vous recevrez un meessage sur {} à la fin du traitement'.format(obj.process_library, user.email))
        pass

    
    # def get_urls(self):

    #     # get the default urls
    #     urls = super(ProcessAdmin, self).get_urls()

    #     # define security urls
    #     security_urls = [
    #         path('add/', self.admin_site.admin_view(self.execute_process)),
    #         # Add here more urls if you want following same logic
    #     ]

    #     # Make sure here you place your added urls first than the admin default urls
    #     return security_urls + urls

    # def execute_process(self,request):
    #     if request.method == 'POST':
    #         form = UploadFileForm(request.POST, request.FILES)
    #         if form.is_valid():
    #             user = request.user
    #             library = Library.objects.get(library_name=form.cleaned_data['library'])
    #             nb_of_line = sum(1 for line in request.FILES['file'])
    #             process = Process( process_library = library,
    #                             process_num_title_to_processed = nb_of_line,
    #                             process_user = user,
    #                             process_job_type = form.cleaned_data['job_type']
    #                         )         
    #             process.save()
    #             logger.info("Process cree")
    #             lines=[]
    #             for line in request.FILES['file']:
    #                 line = line.rstrip()
    #                 clean_ppn = re.search("(^|\(PPN\))([0-9]{8}[0-9Xx]{1})(;|$)", line.decode())
    #                 if clean_ppn  is None :
    #                     logger.debug("{} - N'est pas un PPN valide ".format(line.decode()))
    #                     error = Error(  error_ppn = line.decode(),
    #                             error_type = 'PPN_MAL_FORMATE',
    #                             error_process = process)
    #                     error.save()
    #                 else :
    #                     lines.append(clean_ppn.group(2))
    #             logger.debug(lines)
    #             process.process_num_ppn_mal_formate = Error.objects.filter(error_process=process,error_type='PPN_MAL_FORMATE').count()
    #             process.save()
    #             #Pour l'analyse de recouvrement Alma vers le SUDOC on requête le service de l'abes par lot de 50 PPN 
    #             if process.process_job_type == "ALMA_TO_SUDOC" :
    #                 lines = list(chunks(lines,50))
    #             #Lancement de l'analyse de recouvrement
    #             ExecuteJobThread(lines,process).start()
    #             request.session['pid'] = process.id
    #             messages.success(request, 'L''analyse de recouvrement a été lancée pour la bibliothèque {}. Vous recevrez un meessage sur {} à la fin du traitement'.format(library, user.email))
    #             return HttpResponseRedirect("/admin/sudoc_recouv/process/")

    #     else:
    #         form = UploadFileForm()
    #     return render(request, "sudoc_recouv/execute-process.html", locals())

@admin.register(Error)
class ErrorAdmin(admin.ModelAdmin, ModesExport):
    list_display = ('error_ppn', 'error_type', 'error_process','error_message')
    ordering = ('error_process','error_type')
    list_filter = ['error_process__process_library','error_type']
    search_fields = ['error_ppn', 'error_type']
    actions = ["export_as_csv", "export_as_set"]