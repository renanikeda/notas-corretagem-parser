from reader import ParseCorretagem

# parsePDF = ParseCorretagem(f'D:/User/Documentos/IR')
parsePDF = ParseCorretagem(f'./IR', filter_years_list = [])
parsePDF.generate_summary_file()