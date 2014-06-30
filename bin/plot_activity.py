import bigbang.mailman as mailman
import pandas as pd
from dateutil import parser as dp
import datetime
import matplotlib.pyplot as plt
import numpy as np
import pytz


url = "http://mail.scipy.org/pipermail/scipy-dev/"

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

# just drop the missing values for now
data = pd.DataFrame({'Date':dates,'From':froms}).dropna()

# because sometimes somebody sends a messages from the future
data = data[data['Date'] < datetime.datetime.now(pytz.utc)]

### I've been having trouble getting traction with pandas
### going to go old school on this for a bit

## an array
## * columns are From addresses
## * rows are ordinal days
## * values are number of messages sent From x on day y
from_list = list(set(froms))
days = [d.toordinal() for d in data['Date']]

activity = np.zeros([len(from_list),max(days)-min(days)+1])


# the ordinal day semantics of position 0 in the activity array
day_offset = data['Date'].min().toordinal()

for values in data.values:
    date = values[0]
    m_from = values[1]

    m_from_i = from_list.index(m_from)
    day_i = date.toordinal() - day_offset

    activity[m_from_i,day_i] = activity[m_from_i,day_i] + 1

