# Corretagem Parser
Class to parse XP/RICO Notas de Corretagem in PDF to Excel to ease IR declaration, calculating mean price, gain and loss.
The class ParseCorretagem receives a root path to parse every recap for every year, so it's expect the following file system: {root_path}/{broker}/{year}/Notas de Corretagem/[pdf files] and {root_path}/{broker}/{year}/Proventos/[pdf files].
If you have subscripted in some assets, a subscricao.csv file need to be in the root in csv format Asset; Price; Amount; Date like HGRU11; 126.17; 12; 01/08/2024

