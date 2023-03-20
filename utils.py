import re
regex_date = r'\d{2}/\d{2}/\d{4}'

def parse_number(token):
    try:
        return token[0].replace('.', '').replace(',','.')
    except:
        return token[0]

def filter_obs(token):
    try:
        if 'D' in token[0]:
            return token[0].replace('#', '')
        else: 
            return 'N'
    except:
        return ''

def parse_asset_name(token):
    try:
        asset_regex = r'[A-Z]{4}[1-9]{1,2}'
        return re.search(asset_regex, token[0]).group()
    except:
        return token[0]

start_asset_name = r'FRACIONADO|VISTA'
end_asset_name = r'\s(CI|PNB|UNT|PB|ON|PNA|PN)\s'

