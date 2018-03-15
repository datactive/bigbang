import bigbang.mailman as mm
import os

path = 'archives/'
for subdirectory in os.listdir('archives/'):
        mm.open_list_archives(subdirectory).to_csv(path+subdirectory+'.csv',encoding='utf-8')
