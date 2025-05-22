import base64
import re
from enum import Enum
import pyparsing as pp

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

class FileType(Enum):
    NOTAS = 1
    RENDIMENTOS = 2


special_chars_to_replace = '\xa0'
start_asset_name = r'FRACIONADO|VISTA'
end_asset_name = r'\s(CI|PNB|UNT|PB|ON|PNA|PN)\s'

provento_types = 'RENDIMENTO|DIVIDENDO|JCP|SUBSCRICAO'

block_definition = {
    FileType.NOTAS: {
        'start_line': r'[0-9]-BOVESPA',
        'start_block': r'Negócios realizados.*Ajuste D/C',
        'end_block': r'NOTA DE NEGOCIAÇÃO.*',
    },
    FileType.RENDIMENTOS: {
        'start_line': r'[a-zA-Z0-9]',
        'start_block': r'Pagamento',
        'end_block': r'INFORMAÇÕES COMPLEMENTARES',
    }
}

row_definition = {
    FileType.NOTAS: pp.Regex(regex_date)('data_trade') + pp.Suppress(pp.Literal('BOVESPA')) + pp.Word(pp.alphas)('tipo') + pp.Suppress(pp.Word(start_asset_name)) + pp.SkipTo(pp.Regex(end_asset_name), fail_on = '\n', include=False).set_parse_action(parse_asset_name)('nome') + pp.Suppress(pp.SkipTo(pp.Word(pp.printables) + pp.White() + pp.Word(pp.nums), fail_on = '\n')) + pp.Word(pp.printables).set_parse_action(filter_obs)('Obs') + pp.Word(pp.nums)('quantidade') + pp.Word(pp.nums + ',.')('preco').set_parse_action(parse_number) + pp.Word(pp.nums + ',.')('total').set_parse_action(parse_number),
    FileType.RENDIMENTOS: pp.Word(pp.alphanums)('nome') + pp.Regex(provento_types) + pp.Suppress(pp.SkipTo(pp.Word(pp.nums), include = False, fail_on='\n')) + pp.Word(pp.nums)('quantidade') + pp.Word(pp.nums + ',.')('valor_bruto').set_parse_action(parse_number) + pp.Word(pp.nums + ',.')('valor_ir').set_parse_action(parse_number) + pp.Word(pp.nums + ',.')('valor_liquido').set_parse_action(parse_number) + pp.Regex(regex_date)('data_trade')
}

b3_url_search = "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetInitialCompanies/"
b3_query_search = lambda company: base64.urlsafe_b64encode(str.encode(f'{{"language":"pt-br","pageNumber":1,"pageSize":20,"company":"{company}"}}')).decode()

b3_url_funds_search = "https://sistemaswebb3-listados.b3.com.br/fundsProxy/fundsCall/GetDetailFundSIG/"
b3_query_funds_search = lambda fund: base64.urlsafe_b64encode(str.encode(f'{{"typeFund":7,"cnpj":"0","identifierFund":"{re.sub(r"[0-9]+", "", fund)}"}}')).decode()

b3_ticker = r'[a-zA-Z]{4}\d{1,2}'
de_para_ticker_original = {
    'BRADESPAR': 'BRAP4',
    'TAESA': 'TAEE11',
    'BRASKEM': 'BRKM5',
    'COPEL': 'CPLE6',
    'ITAUSA': 'ITSA4',
    'ITAUUNIBANCO': 'ITUB4',
    'USIMINAS': 'USIM5',
    'BRASIL': 'BBAS3',
    'TRAN PAULIST': 'ISAE4',
    'PETROBRAS': 'PETR4',
    'SANEPAR': 'SAPR4',
    'B3': 'B3SA3',
    'BR PARTNERS': 'BRBI11',
    'IRANI': 'RANI3',
    'ISHARE SP500': 'IVVB11',
    'UNIPAR': 'UNIP6',
    'WIZ CO': 'WIZC3',
    'CSNMINERACAO': 'CMIN3',
    'BBSEGURIDADE': 'BBSE3',
    'SPARTA INFRA': 'JURO11',
    'BOA SAFRA': 'SOJA3',
    'VALE': 'VALE3',
    'JALLESMACHAD': 'JALL3',
    'ENGIE BRASIL': 'ENGIE3',
    'HASHDEX NCI': 'HASH11',
    'VULCABRAS': 'VULC3',
    'UNIFIQUE': 'FIQE3',
    'FII BRESCO': 'BRCO11',
    'FII DEVANT': 'DEVA11',
    'FII HGRU PAX': 'HGRU11',
    'FII KINEA': 'KNRI11',
    'FII MALLS BP': 'MALL11',
    'FII MAXI REN': "MXRF11",
    'FII XP MALLS': "XPML11",
    'SPARTA INFRA': 'JURO11',
    'FII BTLG': 'BTLG11',
    'FII VERSCRI': 'VSLH11'
}
def expand_dict(data: dict) -> dict:
    result = data.copy()
    for key in data:
        if isinstance(key, str):
            no_space_key = key.replace(" ", "")
            if no_space_key != key:
                result[no_space_key] = data[key]
    return result

de_para_ticker = expand_dict(de_para_ticker_original)
