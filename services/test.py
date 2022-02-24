import xml.etree.ElementTree as ET
ns = {'sru': 'http://www.loc.gov/zing/srw/',
        'marc': 'http://www.loc.gov/MARC21/slim',
        'diag':  'http://www.loc.gov/zing/srw/diagnostic/'}
country_data_as_string = "<?xml version='1.0' encoding='UTF-8' standalone='no'?><searchRetrieveResponse xmlns='http://www.loc.gov/zing/srw/' xmlns:diag='http://www.loc.gov/zing/srw/diagnostic/'><version>1.2</version><diagnostics><diag:diagnostic><diag:uri>200801</diag:uri><diag:message>Catalog search has encountered an error</diag:message></diag:diagnostic></diagnostics></searchRetrieveResponse>"
root = ET.fromstring(country_data_as_string)
print (root.tag)
print(root[1].tag)
print(root.find("sru:diagnostics/diag:diagnostic/diag:message",ns).text)
