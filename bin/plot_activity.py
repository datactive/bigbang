import bigbang.mailman as mailman
import bigbang.graph as graph
from bigbang.parse import get_date
from bigbang.functions import *
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import numpy as np
import math
import pytz


def process_messages(messages):
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

    return dates, froms, broke

def to_dataframe(dates,froms):
    # just drop the missing values for now
    data = pd.DataFrame({'Date':dates,'From':froms}).dropna()

    # because sometimes somebody sends a messages from the future
    data = data[data['Date'] < datetime.datetime.now(pytz.utc)]

    return data


def activity(messages):
    dates, froms, broke = process_messages(messages)

    data = to_dataframe(dates,froms)

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

    return activity, np.arange(min(days),max(days)+1)


def plot_ascendancy(messages):
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

    return ascendancy, capacity


url1 = "http://mail.scipy.org/pipermail/ipython-dev/"
url2 = "http://mail.scipy.org/pipermail/ipython-user/"

messages1 = mailman.open_list_archives(url1)
messages2 = mailman.open_list_archives(url2)

activity1,dates1 = activity(messages1)
activity2,dates2  = activity(messages2)


total_activity1 = np.sum(activity1,0)
total_activity2 = np.sum(activity2,0)

participant_activity1 = np.sum(activity1 > 0,0)
participant_activity2 = np.sum(activity2 > 0,0)

plt.plot_date(dates1,smooth(total_activity1,50),'r',label="dev activity",xdate=True)
plt.plot_date(dates2,smooth(total_activity2,50),'b',label="user activity",xdate=True)
plt.legend()
plt.show()

plt.plot_date(dates1,smooth(participant_activity1,50),'r',label="dev participants",xdate=True)
plt.plot_date(dates2,smooth(participant_activity2,50),'b',label="user participants",xdate=True)
plt.legend()
plt.show()


#plt.plot(ascendancy,'o')
#plt.plot(capacity,'y')

#plt.show()
