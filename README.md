# Programme d'analyse de recouvrement

Ce programme est un module Django qui permet de conduire des analyses de recouvrement des collections d'une bibliothèque donnée avec les localisations SUDOC et inversement. Il premet d'identifier les notices désynchronisées. Le programme prend en paramètre une liste de PPN à téléversé dans un fichier. 

L'analyse peut être conduite de Alma vers le SUDOC ou du Sudoc vers Alma


## Rapport d'analyse
Le programme produit un rapport d'analyse indiquant les erreurs suivantes.
| Code erreur| Description |
| --- | --- |
| PPN_INCONNU_SUDOC | PPN inconnu dans le SUDOC|
| PPN_INCONNU_ALMA | PPN inconnu dans Alma|
| LOC_INCONNUE_ALMA | Pas de localisation correspondante dans Alma|
| LOC_INCONNUE_SUDOC | Pas de localisation correspondante dans le SUDOC|
| PPN_MAL_FORMATE | PPN mal formaté|
| DOUBLON_ALMA | Plusieurs notices ont été trouvées dans Alma avec le même PPN|
| ERREUR_REQUETE | Erreur lors de l''appel au sru Alma ou au webservice Abes|

Les rapports

## Bibliothèques et RCR

Le programme nécessite l'alimentation de la table "Bibliothèques et RCR" ([Libraries](./models.py)). Chaque bibliothèque doit avoir un nom, un id alma, un rcr et une institution de rattachement (utile dans le cadre d'une topologie réseau).

Pour les bibliothèques ayant des collections localisées dans une bibliothèque temporaire. Il faut ajouter la localisation temporaire à la table *Bibliothèques et RCR* en l'associant au RCR de l abibliothèque permanente.

