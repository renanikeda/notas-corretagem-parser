from utils import regex_date, parse_number, filter_obs, start_asset_name, end_asset_name, parse_asset_name, de_para_ticker, b3_url_search, b3_query_search, b3_url_funds_search, b3_query_funds_search, provento_types, special_chars_to_replace, block_definition, row_definition, FileType
from datetime import datetime
from PyPDF2 import PdfReader
import pyparsing as pp
from copy import copy
import pandas as pd
import numpy as np
import requests
import random
import time
import os
import re

pd.options.mode.chained_assignment = None
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=DeprecationWarning)

class ParseCorretagem():
    def __init__(self, path = "12_2022.pdf", filter_years_list = []):
        self.path = path
        self.filter_years_list = filter_years_list
        self.reset_cache()
    
    def reset_cache(self):
        self.parsed_pdf = None
        self.pd_parsed_pdf = pd.DataFrame()
        self.rows_pdf = None
        
    def get_reader(self, file_type = FileType.NOTAS):
        files_path = []
        file_type_dir = "Notas de Corretagem" if file_type == FileType.NOTAS else "Proventos"

        if (self.path.split('.')[-1] == 'pdf'):
            files_path._append(self.path)
        else:
            for broker in filter(lambda dir: '.' not in dir, os.listdir(self.path)):
                for file_year in os.listdir(f'{self.path}/{broker}'):
                    if self.filter_years_list and file_year not in self.filter_years_list: continue

                    full_path = f"{self.path}/{broker}/{file_year}/{file_type_dir}"
                    print(f'Seaching path {full_path}/*.pdf')
                    files = filter(lambda file: '.pdf' in file, os.listdir(f'{full_path}'))
                    files_path = [*files_path, *list(map(lambda file: f'{full_path}/{file}', files))]

            self.readers = [PdfReader(file) for file in files_path]

        return self.readers

    def generate_rows(self, file_type = FileType.NOTAS):
        self.get_reader(file_type)
        block = block_definition[file_type]
        rows_pdf = ''
        for reader in self.readers:
            for page in reader.pages:
                text_page = page.extract_text()
                text_page = re.sub(special_chars_to_replace, '', text_page)
                text_page = re.sub('\n+', ' ', text_page)
                if file_type == FileType.NOTAS:
                    data_trade = re.search(r'(?<=Data pregão) ' + regex_date, text_page)
                    data_trade = data_trade.group() if data_trade else ''
                    text_page = re.sub(block['start_line'], '\n' + data_trade + ' ' + block['start_line'].replace('[0-9]-',''), text_page)

                text_page = re.sub(block['start_block'] + '|' + block['end_block'] + '|', '', text_page)
                rows_pdf += text_page
        self.rows_pdf = rows_pdf

        return rows_pdf

    def parse(self, file_type = FileType.NOTAS, pattern = None):
        self.default_row_pattern = row_definition[file_type]
        if not self.rows_pdf:
            self.generate_rows(file_type)
        block = self.rows_pdf
        row_pattern = self.default_row_pattern if pattern is None else pattern
        self.parsed_pdf = row_pattern.searchString(block)
        return self.parsed_pdf
    
    def get_trades(self):
        if not self.parsed_pdf:
            self.parse(FileType.NOTAS)
        columns = ['Data Trade', 'Tipo', 'Nome', 'Obs', 'Quantidade', 'Preço', 'Total']
        if self.pd_parsed_pdf.empty:
            pdParsedPdf = pd.DataFrame(self.parsed_pdf, columns = columns)
            pdParsedPdf['Quantidade'] = pdParsedPdf['Quantidade'].astype(float)
            pdParsedPdf['Preço'] = pdParsedPdf['Preço'].astype(float)
            pdParsedPdf['Total'] = pdParsedPdf['Total'].astype(float)
            pdParsedPdf.loc[pdParsedPdf['Tipo'] == 'V', 'Quantidade'] = pdParsedPdf.loc[pdParsedPdf['Tipo'] == 'V', 'Quantidade']*(-1)
            pdParsedPdf['Nome'] = pdParsedPdf['Nome'].apply(lambda nome: de_para_ticker.get(nome.strip(), nome.strip()))
            pdParsedPdf.sort_values('Data Trade', inplace=True, key=lambda col: pd.to_datetime(col, format="%d/%m/%Y", dayfirst=True))
            self.pd_parsed_pdf = pdParsedPdf
        return self.pd_parsed_pdf
    
    def get_rendimentos(self):
        if not self.parsed_pdf:
            self.parse(FileType.RENDIMENTOS)
        columns = ['Nome', 'Tipo', 'Quantidade', 'Valor Bruto', 'Valor IR', 'Valor Liquido', 'Data Trade']

        # print(self.parsed_pdf)
        if self.pd_parsed_pdf.empty:
            pdParsedPdf = pd.DataFrame(self.parsed_pdf, columns = columns)
            pdParsedPdf['Quantidade'] = pdParsedPdf['Quantidade'].astype(float)
            pdParsedPdf['Valor Bruto'] = pdParsedPdf['Valor Bruto'].astype(float)
            pdParsedPdf['Valor IR'] = pdParsedPdf['Valor IR'].astype(float)
            pdParsedPdf['Valor Liquido'] = pdParsedPdf['Valor Liquido'].astype(float)

            pdParsedPdf['Nome'] = pdParsedPdf['Nome'].apply(lambda nome: de_para_ticker.get(nome.strip(), nome.strip()))

            pdParsedPdf['Ano'] = pd.to_datetime(pdParsedPdf['Data Trade'], dayfirst=True).dt.year
            pdParsedPdf = pdParsedPdf.groupby(['Nome', 'Tipo', 'Ano']).agg({ 'Valor Bruto': 'sum', 'Valor IR': 'sum', 'Valor Liquido': 'sum', 'Data Trade': 'min'}).reset_index()
            pdParsedPdf.sort_values('Data Trade', inplace=True, key=lambda col: pd.to_datetime(col, format="%d/%m/%Y", dayfirst=True))
            self.pd_parsed_pdf = pdParsedPdf
        return self.pd_parsed_pdf
    
    def get_trades_with_subscription(self, full_path = ''):
        self.get_trades()
        subscriptions_df = self.transform_subsciption_to_trade(full_path)
        self.pd_parsed_pdf = self.pd_parsed_pdf._append(subscriptions_df, ignore_index = True)
        self.pd_parsed_pdf.sort_values('Data Trade', inplace=True, key=lambda col: pd.to_datetime(col, format="%d/%m/%Y", dayfirst=True))
        return self.pd_parsed_pdf
       
    def setup_b3_info(self, asset, amount, mean_price):
        try:
            url = b3_url_search + b3_query_search(asset)
            res = requests.get(url, timeout=5)
            if res.status_code == 200 and res.json()['results']:
                b3_info = res.json()['results'][0]
                return f"{amount} Ações {b3_info.get('companyName', '').strip()} ({b3_info.get('cnpj', '')}) - Corretora XP INVESTIMENTOS (02.332.886/0001-04)  {mean_price}"

            url = b3_url_funds_search + b3_query_funds_search(asset)
            res = requests.get(url, timeout=5)
            
            if res.status_code == 200 and res.json():
                b3_info = res.json()
                return f"{amount} Ações {b3_info['detailFund'].get('companyName', '').strip()} ({b3_info['detailFund'].get('cnpj', '')}) - ADM {b3_info['shareHolder'].get('shareHolderName', '').strip()} - Corretora XP INVESTIMENTOS (02.332.886/0001-04)  {mean_price}"
            return ''
        except:
            print(f"Asset {asset} not found in B3")
            return f"{amount} Ações - Corretora XP INVESTIMENTOS (02.332.886/0001-04)  {mean_price}"
        
    def mean_price(self):
        pdParsedPdf = self.get_trades()
        assets = pdParsedPdf['Nome'].unique()
        mean_df = pd.DataFrame([], columns = ['Nome', 'Quantidade', 'Preço Médio', 'Posição Final'])
        for asset in assets:
            subDf = pdParsedPdf[(pdParsedPdf['Nome'] == asset) & (pdParsedPdf['Tipo'] == 'C')]
            if subDf.empty: continue

            mean_price = subDf.groupby('Nome').apply(lambda df: round(np.average(df['Preço'], weights=df['Quantidade']), 2)).values[0]

            subDf = pdParsedPdf[pdParsedPdf['Nome'] == asset]
            quantity = (subDf['Quantidade'].sum(numeric_only = True))
            position = round((subDf['Preço']*subDf['Quantidade']).sum(), 2)
            if quantity == 0: position = 0
            
            mean_df.loc[len(mean_df)] = { 'Nome': asset, 'Quantidade': quantity, 'Preço Médio': mean_price, 'Posição Final': position } 
        self.mean_df = mean_df
        return mean_df

    def trade_gain_and_losses(self):
        pdParsedPdf = self.get_trades()
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
                    gainLossDf = gainLossDf._append({'Data Trade': rowSubDf['Data Trade'], 'Nome': rowSubDf['Nome'], 'Operação': rowSubDf['Obs'], 'Quantidade': rowSubDf['Quantidade'], 'Preço Médio': current_mean_price, 'Preço Venda': selling_price, 'Lucros ou Prejuizos': gain_loss}, ignore_index = True)
                    gainLossDf.sort_values('Data Trade', inplace=True, key=lambda col: pd.to_datetime(col, format="%d/%m/%Y", dayfirst=True))
        return gainLossDf
    
    def add_b3_info_to_mean_price(self):
        final_mean_df = pd.DataFrame([], columns = [*self.mean_df.columns, "IR Info"])
        for _, row in self.mean_df.iterrows():
            b3_info = self.setup_b3_info(row['Nome'], row['Quantidade'], row['Preço Médio'])
            final_mean_df = final_mean_df._append({ 'Nome': row['Nome'], 'Quantidade': row['Quantidade'], 'Preço Médio': row['Preço Médio'], 'Posição Final': row['Posição Final'], 'DIVIDENDO': row['DIVIDENDO'], 'JCP': row['JCP'], 'RENDIMENTO': row['RENDIMENTO'], 'IR Info': copy(b3_info)}, ignore_index = True)
            time.sleep(random.randint(200, 1000)*0.001)
        final_mean_df['IR Info'] = final_mean_df['IR Info'].astype(str).str.strip()
        return final_mean_df

    def merge_mean_price_rendimentos(self, mean_df, rendimentos_pd, year):
        new_mean_df = pd.DataFrame([], columns = [*self.mean_df.columns, *provento_types.split("|")])
        filtered_rendimentos_pd = rendimentos_pd[rendimentos_pd["Ano"] == int(year)]

        for _, row in self.mean_df.iterrows():
            asset = row['Nome']
            asset_rendimentos = filtered_rendimentos_pd[filtered_rendimentos_pd['Nome'] == asset]
            rendimentos = dict(zip(asset_rendimentos['Tipo'], asset_rendimentos['Valor Liquido']))

            new_mean_df = new_mean_df._append({ 'Nome': row['Nome'], 'Quantidade': row['Quantidade'], 'Preço Médio': row['Preço Médio'], 'Posição Final': row['Posição Final'], 'DIVIDENDO': rendimentos.get('DIVIDENDO', ''),  'JCP': rendimentos.get('JCP', ''),  'RENDIMENTO': rendimentos.get('RENDIMENTO', '')}, ignore_index = True)
            
        self.mean_df = new_mean_df
        return new_mean_df

    def generate_summary_file(self):
        pdParsedPdf = self.get_trades_with_subscription()
        pdMeanPdf = self.mean_price()

        pdTradesPdf = self.trade_gain_and_losses()
        self.reset_cache()
        pdRendimentosPdf = self.get_rendimentos()

        last_year = int(datetime.now().year) - 1
        pdMeanPdf = self.merge_mean_price_rendimentos(pdMeanPdf, pdRendimentosPdf, last_year)


        pdMeanPdf = self.add_b3_info_to_mean_price()

        file_to_save = f"Notas_Parseadas_{datetime.now().year}.xlsx"
        file_already_exists = file_to_save in os.listdir()

        mode = 'a' if file_already_exists else 'w'
        if_sheet_exists = 'replace' if file_already_exists else None 

        writer = pd.ExcelWriter(file_to_save, engine = 'openpyxl', mode = mode, if_sheet_exists = if_sheet_exists)

        pdParsedPdf.to_excel(writer, sheet_name="Nota", index=False)
        pdMeanPdf.to_excel(writer, sheet_name="Preco Medio", index=False)
        pdTradesPdf.to_excel(writer, sheet_name="Ganhos e Perdas", index=False)
        pdRendimentosPdf.to_excel(writer, sheet_name="Rendimentos", index=False)

        
        writer.close()
        print('Saved!')

    def transform_subsciption_to_trade(self, full_path = ''):
        original_columns = ['Nome', 'Preço', 'Quantidade', 'Data Trade']
        trade_columns = ['Data Trade', 'Tipo', 'Nome', 'Obs', 'Quantidade', 'Preço', 'Total']
        path = self.path + '/subscricoes.csv' if not full_path else full_path
        
        if not 'subscricoes.csv' in os.listdir(self.path): return pd.DataFrame(columns=trade_columns)
        df = pd.read_csv(path, sep=',', header=None)
        df.columns = original_columns
        df['Preço'] = df['Preço'].str.replace(',', '.').astype(float)
        df['Quantidade'] = pd.to_numeric(df['Quantidade'], errors='coerce')
        df['Tipo'] = 'C'
        df['Obs'] = 'N'
        df['Total'] = df['Preço'] * df['Quantidade']
        df = df[trade_columns]
        return df

# parsePDF = ParseCorretagem(f'D:/User/Documentos/IR')
parsePDF = ParseCorretagem(f'./IR', filter_years_list = [])
parsePDF.generate_summary_file()