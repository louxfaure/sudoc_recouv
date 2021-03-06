from django import forms
from .models import Process 
from .validators import file_extention_validator

class UploadFileForm(forms.ModelForm):
    file_sudoc = forms.FileField(label='Télécharger votre fichier de PPN extraits du SUDOC',validators=[file_extention_validator])
    file_alma = forms.FileField(label="Télécharger votre fichier de PPN extraits d'Alma",validators=[file_extention_validator])

    class Meta:
        model = Process
        fields = ['process_library','file_sudoc','file_alma']
    # library = forms. (label='Bibliothèque',queryset=Library.objects.order_by('library_name'), required=True)
    # file = forms.FileField(label='Télécharger votre fichier de PPN')
    # job_types_list = [  ("ALMA_TO_SUDOC", "Comparer les localisations Alma avec les localisations SUDOC"),
    #                     ("SUDOC_TO_ALMA", "Comparer les localisations SUDOC avec les localisations ALMA")]
    # job_type = forms.ChoiceField(choices=job_types_list, required=True, label='Type d''analyse de recouvrement') 