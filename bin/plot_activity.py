import bigbang.mailman as mailman
import bigbang.graph as graph
from bigbang.parse import get_date
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import numpy as np
import math
import pytz

URLS_FILE = "urls.txt"
for url in open(URLS_FILE):
    url = url.rstrip()
    break  # just grab the first one, for now

messages = mailman.open_list_archives(url)

dates = []
froms = []
broke = []

for m in messages:
    m_from = m.get('From')
    froms.append(m_from)
    
    try:
        date = get_date(m)

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

# take an array of data D, divide it into B bins
# each containing the sum of the consequetive len(D)/B
# entries
#def rebin(d,b):
#    bin_width = math.floor(len(d) / b)
#    return bin_width # broken

# smooth out values by average over adjacent n
def smooth(d,n):
    o = np.zeros(len(d))

    for i in range(n):
        o += np.roll(d,i)

    o = o / n

    return o


for values in data.values:
    date = values[0]
    m_from = values[1]

    m_from_i = from_list.index(m_from)
    day_i = date.toordinal() - day_offset

    activity[m_from_i,day_i] = activity[m_from_i,day_i] + 1

total_activity = np.sum(activity,0)
participant_activity = np.sum(activity > 0,0)

plt.plot(smooth(total_activity,100),'r')
plt.plot(smooth(participant_activity,100),'b')
plt.show()

IG = graph.messages_to_interaction_graph(messages)
matrix = graph.interaction_graph_to_matrix(IG)

# removing last email in case it was sent in 2083.
# don't ask
#sorted_messages = sorted(messages,key=get_date)[:-1]

dated_messages = {}

for m in messages:
    o = get_date(m).toordinal()

    dated_messages[o] = dated_messages.get(o,[])
    dated_messages[o].append(m)


epoch = max(days)-min(days)

step = 1
duration = 100

ascendancy = np.zeros([max(days)-min(days)+1])
capacity = np.zeros(([max(days)-min(days)+1]))


for i in range(epoch/step):
    min_d = min(days) + i * step
    max_d = min_d + duration

    block_messages = []

    for d in range(min_d,max_d):
        block_messages.extend(dated_messages.get(d,[]))

    b_IG = graph.messages_to_interaction_graph(block_messages)
    b_matrix = graph.interaction_graph_to_matrix(b_IG)

    ascendancy[min_d-day_offset] = graph.ascendancy(b_matrix)
    capacity[min_d-day_offset] = graph.capacity(b_matrix)

plt.plot(ascendancy,'o')
plt.plot(capacity,'y')

plt.show()
