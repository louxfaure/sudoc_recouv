from django.core.exceptions import ValidationError


def file_extention_validator(file):
    """Valide l'extention du fichier 
    Args:
        file ([type]): [description]

    Raises:
        ValidationError: [description]
    """
    # Teste l'extention du fichier
    if not file.name.endswith(('.csv','.txt','tsv')) :
        raise ValidationError('Le fichier doit être un fichier csv, txt ou tsv')

