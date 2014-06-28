import bigbang.mailman as mailman
import pandas as pd
from dateutil import parser as dp
import matplotlib.pyplot as plt
import numpy as np
import pytz


url = "http://mail.scipy.org/pipermail/numpy-discussion/"

messages = mailman.open_list_archives(url)

dates = []
froms = []
broke = []

for m in messages:
    m_from = m.get('From')
    froms.append(m_from)
    
    try:
        date = dp.parse(m.get('Date'))

        if date.tzinfo is None:
            date = pytz.utc.localize(date)

        dates.append(date)

    except Exception as e:
        print e
        dates.append(pd.NaT)
        broke.append(m)

data = pd.DataFrame({'Date':dates,'From':froms})
