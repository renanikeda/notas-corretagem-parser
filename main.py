from reader import ParseCorretagem

# parsePDF = ParseCorretagem(f'D:/User/Documentos/IR')
parsePDF = ParseCorretagem(f'./IR', filter_years_list = ['2024'])
parsePDF.generate_summary_file()