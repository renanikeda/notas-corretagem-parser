from PyPDF2 import PdfReader
import pyparsing as pp
import pandas as pd
import os
import re

pd.options.mode.chained_assignment = None
class ParseCorretagem():
    def __init__(self, path = "12_2022.pdf") -> None:
        self.path = path
        if (path.split('.')[-1] == 'pdf'):
            files_path = [path]
        else:
            files = filter(lambda file: '.pdf' in file, os.listdir(path))
            files_path = map(lambda file: path + '/' + file, files)
        self.readers = [PdfReader(file) for file in files_path]
        self.start_line = '1-BOVESPA'
        self.start_block = r'Negócios realizados.*Ajuste D/C'
        self.end_block = 'NOTA DE NEGOCIAÇÃO.*'
            
    def generate_rows(self):
        parsed_pdf = ''
        for reader in self.readers:
            for page in reader.pages:
                text = page.extract_text()
                text = re.sub('\n+', ' ', text)
                data_trade = re.search(r'(?<=Data pregão) \d{2}/\d{2}/\d{4}',text)
                data_trade = data_trade.group() if data_trade else ''
                text = re.sub(self.start_block + '|' + self.end_block + '|', '', text)
                text = re.sub(self.start_line, '\n' + data_trade + ' ' + self.start_line, text)
                parsed_pdf += text
        self.parsed_pdf = parsed_pdf
        return parsed_pdf

    def parse(self):
        block = self.generate_rows()
        row_pattern = pp.Regex(r'\d{2}/\d{2}/\d{4}')('data_trade') + pp.Suppress(pp.Literal('1-BOVESPA')) + pp.Word(pp.alphas)('tipo') + pp.Suppress(pp.Word(pp.alphas)) + pp.Word(pp.alphas)('nome') + pp.Suppress(pp.SkipTo(pp.White() + pp.Word(pp.nums), fail_on = '\n')) + pp.Word(pp.nums)('quantidade') + pp.Word(pp.nums + ',.')('preco') + pp.Word(pp.nums + ',.')('total')
        return row_pattern.searchString(block)
    
parsedPdf = ParseCorretagem('D:/User/Documentos/IR/2022/Rico/Nota de Corretagem').parse()
pdParsedPdf = pd.DataFrame(parsedPdf, columns=['Data Trade', 'Tipo', 'Nome', 'Quantidade', 'Preço', 'Total'])
pdParsedPdf.to_excel('teste.xlsx', sheet_name="Nota", index=False)
print(parsedPdf)