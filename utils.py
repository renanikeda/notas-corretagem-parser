
regex_date = r'\d{2}/\d{2}/\d{4}'

def parse_number(token):
    try:
        return token[0].replace(',',':').replace('.', ',').replace(':', '.')
    except:
        return token[0]