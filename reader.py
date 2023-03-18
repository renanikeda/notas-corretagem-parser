from PyPDF2 import PdfReader
from utils import regex_date, parse_number
import pyparsing as pp
import pandas as pd
import os
import re

pd.options.mode.chained_assignment = None

class ParseCorretagem():
    def __init__(self, path = "12_2022.pdf", start_line = '1-BOVESPA', start_block = r'Negócios realizados.*Ajuste D/C', end_block = r'NOTA DE NEGOCIAÇÃO.*'):
        self.path = path
        if (path.split('.')[-1] == 'pdf'):
            files_path = [path]
        else:
            files = filter(lambda file: '.pdf' in file, os.listdir(path))
            files_path = map(lambda file: path + '/' + file, files)

        self.readers = [PdfReader(file) for file in files_path]
        self.start_line = start_line
        self.start_block = start_block
        self.end_block = end_block
        self.default_row_pattern = pp.Regex(regex_date)('data_trade') + pp.Suppress(pp.Literal('1-BOVESPA')) + pp.Word(pp.alphas)('tipo') + pp.Suppress(pp.Word(pp.alphas)) + pp.Word(pp.alphas)('nome') + pp.Suppress(pp.SkipTo(pp.White() + pp.Word(pp.nums), fail_on = '\n')) + pp.Word(pp.nums)('quantidade') + pp.Word(pp.nums + ',.')('preco').set_parse_action(parse_number) + pp.Word(pp.nums + ',.')('total').set_parse_action(parse_number)
            
    def generate_rows(self):
        parsed_pdf = ''
        for reader in self.readers:
            for page in reader.pages:
                text_page = page.extract_text()
                text_page = re.sub('\n+', ' ', text_page)
                data_trade = re.search(r'(?<=Data pregão) ' + regex_date, text_page)
                data_trade = data_trade.group() if data_trade else ''
                text_page = re.sub(self.start_block + '|' + self.end_block + '|', '', text_page)
                text_page = re.sub(self.start_line, '\n' + data_trade + ' ' + self.start_line, text_page)
                parsed_pdf += text_page
        self.parsed_pdf = parsed_pdf
        return parsed_pdf

    def parse(self, pattern = None):
        block = self.generate_rows()
        row_pattern = self.default_row_pattern if pattern is None else pattern
        return row_pattern.searchString(block)
    
parsedPdf = ParseCorretagem('D:/User/Documentos/IR/2022/Rico/Nota de Corretagem').parse()
pdParsedPdf = pd.DataFrame(parsedPdf, columns=['Data Trade', 'Tipo', 'Nome', 'Quantidade', 'Preço', 'Total'])
pdParsedPdf['Quantidade'] = pdParsedPdf['Quantidade'].astype(float)
pdParsedPdf.to_excel('Notas_Parseadas.xlsx', sheet_name="Nota", index=False)
print(pdParsedPdf['Total'])