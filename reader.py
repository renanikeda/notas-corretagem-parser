from PyPDF2 import PdfReader
from utils import regex_date, parse_number, filter_obs, start_asset_name, end_asset_name, parse_asset_name
from datetime import datetime
import pyparsing as pp
import pandas as pd
import numpy as np
import os
import re

pd.options.mode.chained_assignment = None
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class ParseCorretagem():
    def __init__(self, path = "12_2022.pdf", start_line = '1-BOVESPA', start_block = r'Negócios realizados.*Ajuste D/C', end_block = r'NOTA DE NEGOCIAÇÃO.*'):
        self.path = path
        files_path = []
        if (path.split('.')[-1] == 'pdf'):
            files_path.append(path)
        else:
            for broker in filter(lambda dir: '.' not in dir, os.listdir(self.path)):
                for file_year in os.listdir(f'{self.path}/{broker}'):
                    print(f'Seaching path {self.path}/{broker}/{file_year}/Notas de Corretagem/*.pdf')
                    files = filter(lambda file: '.pdf' in file, os.listdir(f'{self.path}/{broker}/{file_year}/Notas de Corretagem'))
                    files_path = [*files_path, *list(map(lambda file: f'{self.path}/{broker}/{file_year}/Notas de Corretagem/{file}', files))]
        # print(files_path)
        self.readers = [PdfReader(file) for file in files_path]
        self.start_line = start_line
        self.start_block = start_block
        self.end_block = end_block
        self.default_row_pattern = pp.Regex(regex_date)('data_trade') + pp.Suppress(pp.Literal('1-BOVESPA')) + pp.Word(pp.alphas)('tipo') + pp.Suppress(pp.Word(start_asset_name)) + pp.SkipTo(pp.Regex(end_asset_name), fail_on = '\n', include=False).set_parse_action(parse_asset_name)('nome') + pp.Suppress(pp.SkipTo(pp.Word(pp.printables) + pp.White() + pp.Word(pp.nums), fail_on = '\n')) + pp.Word(pp.printables).set_parse_action(filter_obs)('Obs') + pp.Word(pp.nums)('quantidade') + pp.Word(pp.nums + ',.')('preco').set_parse_action(parse_number) + pp.Word(pp.nums + ',.')('total').set_parse_action(parse_number)
        self.columns = ['Data Trade', 'Tipo', 'Nome', 'Obs', 'Quantidade', 'Preço', 'Total']
        self.parsed_pdf = None
        self.pd_parsed_pdf = pd.DataFrame()
        self.rows_pdf = None
            
    def generate_rows(self):
        rows_pdf = ''
        for reader in self.readers:
            for page in reader.pages:
                text_page = page.extract_text()
                text_page = re.sub('\n+', ' ', text_page)
                data_trade = re.search(r'(?<=Data pregão) ' + regex_date, text_page)
                data_trade = data_trade.group() if data_trade else ''
                text_page = re.sub(self.start_block + '|' + self.end_block + '|', '', text_page)
                text_page = re.sub(self.start_line, '\n' + data_trade + ' ' + self.start_line, text_page)
                rows_pdf += text_page
        self.rows_pdf = rows_pdf
        #print(rows_pdf)
        return rows_pdf

    def parse(self, pattern = None):
        if not self.rows_pdf:
            self.generate_rows()
        block = self.rows_pdf
        row_pattern = self.default_row_pattern if pattern is None else pattern
        self.parsed_pdf = row_pattern.searchString(block)
        #print(self.parsed_pdf)
        return self.parsed_pdf
    
    def get_df(self):
        if not self.parsed_pdf:
            self.parse()
        if self.pd_parsed_pdf.empty:
            pdParsedPdf = pd.DataFrame(self.parsed_pdf, columns = self.columns)
            pdParsedPdf['Quantidade'] = pdParsedPdf['Quantidade'].astype(float)
            pdParsedPdf['Preço'] = pdParsedPdf['Preço'].astype(float)
            pdParsedPdf['Total'] = pdParsedPdf['Total'].astype(float)
            pdParsedPdf.loc[pdParsedPdf['Tipo'] == 'V', 'Quantidade'] = pdParsedPdf.loc[pdParsedPdf['Tipo'] == 'V', 'Quantidade']*(-1)

            pdParsedPdf.sort_values('Data Trade', inplace=True, key=lambda col: pd.to_datetime(col, format="%d/%m/%Y", dayfirst=True))
            self.pd_parsed_pdf = pdParsedPdf
        return self.pd_parsed_pdf
    
    def mean_price(self):
        pdParsedPdf = self.get_df()
        assets = pdParsedPdf['Nome'].unique()
        mean_df = pd.DataFrame([], columns = ['Nome', 'Quantidade', 'Preço Médio', 'Posição Final'])
        for asset in assets:
            subDf = pdParsedPdf[(pdParsedPdf['Nome'] == asset) & (pdParsedPdf['Tipo'] == 'C')]
            mean_price = subDf.groupby('Nome').apply(lambda df: round(np.average(df['Preço'], weights=df['Quantidade']), 2)).values[0]

            subDf = pdParsedPdf[pdParsedPdf['Nome'] == asset]
            notional = (subDf['Quantidade'].sum(numeric_only = True))
            position = round((subDf['Preço']*subDf['Quantidade']).sum(), 2)
            if notional == 0: position = 0

            mean_df.loc[len(mean_df)] = { 'Nome': asset, 'Quantidade': notional, 'Preço Médio': mean_price, 'Posição Final': position } 
        return mean_df

    def trade_gain_and_losses(self):
        pdParsedPdf = self.get_df()
        assets = pdParsedPdf['Nome'].unique()
        columns_gain_loss = ['Data Trade', 'Nome', 'Quantidade', 'Operação', 'Preço Médio', 'Preço Venda', 'Lucros ou Prejuizos']
        gainLossDf = pd.DataFrame(columns = columns_gain_loss)
        for asset in assets:
            subDf = pdParsedPdf[(pdParsedPdf['Nome'] == asset)]
            sum_price = 0
            count = 0
            for (_, rowSubDf) in subDf.iterrows():
                if rowSubDf['Tipo'] == 'C':
                    sum_price += rowSubDf['Quantidade'] * rowSubDf['Preço']
                    count += rowSubDf['Quantidade']
                else:
                    current_mean_price = sum_price / count if count > 0 else 0
                    selling_price = rowSubDf['Preço']
                    gain_loss = (selling_price - current_mean_price) * abs(rowSubDf['Quantidade'])
                    gainLossDf = gainLossDf.append({'Data Trade': rowSubDf['Data Trade'], 'Nome': rowSubDf['Nome'], 'Operação': rowSubDf['Obs'], 'Quantidade': rowSubDf['Quantidade'], 'Preço Médio': current_mean_price, 'Preço Venda': selling_price, 'Lucros ou Prejuizos': gain_loss}, ignore_index = True)
                    gainLossDf.sort_values('Data Trade', inplace=True, key=lambda col: pd.to_datetime(col, format="%d/%m/%Y", dayfirst=True))
        return gainLossDf

parsePDF = ParseCorretagem(f'D:/User/Documentos/IR')
pdParsedPdf = parsePDF.get_df()
pdMeanPdf = parsePDF.mean_price()
pdTradesPdf = parsePDF.trade_gain_and_losses()

file_to_save = f"Notas_Parseadas_{datetime.now().year}.xlsx"
file_already_exists = file_to_save in os.listdir()

mode = 'a' if file_already_exists else 'w'
if_sheet_exists = 'replace' if file_already_exists else None 

writer = pd.ExcelWriter(file_to_save, engine = 'openpyxl', mode = mode, if_sheet_exists = if_sheet_exists)

pdParsedPdf.to_excel(writer, sheet_name="Nota", index=False)
pdMeanPdf.to_excel(writer, sheet_name="Preco Medio", index=False)
pdTradesPdf.to_excel(writer, sheet_name="Ganhos e Perdas", index=False)
writer.close()
print('Saved!')