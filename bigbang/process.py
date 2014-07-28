import bigbang.graph as graph
from bigbang.parse import get_date
import pandas as pd
import datetime
import numpy as np
#import math
import pytz
#import pickle
#import os


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

    return activity, np.arange(min(days),max(days)+1), from_list

def compute_ascendancy(messages,duration=50):
    print('compute ascendancy')
    dated_messages = {}

    for m in messages:
        d = get_date(m)

        if d is not None and d < datetime.datetime.now(pytz.utc):
            o = d.toordinal()        
            dated_messages[o] = dated_messages.get(o,[])
            dated_messages[o].append(m)

    days = [k for k in dated_messages.keys()]
    day_offset = min(days)
    epoch = max(days)-min(days)

    ascendancy = np.zeros([max(days)-min(days)+1])
    capacity = np.zeros(([max(days)-min(days)+1]))

    for i in range(epoch):
        min_d = min(days) + i
        max_d = min_d + duration

        block_messages = []

        for d in range(min_d,max_d):
            block_messages.extend(dated_messages.get(d,[]))

        b_IG = graph.messages_to_interaction_graph(block_messages)
        b_matrix = graph.interaction_graph_to_matrix(b_IG)

        ascendancy[min_d-day_offset] = graph.ascendancy(b_matrix)
        capacity[min_d-day_offset] = graph.capacity(b_matrix)

    return ascendancy, capacity

# This is a touch hacky.
# Better to use numpy convolve
# http://stackoverflow.com/questions/11352047/finding-moving-average-from-data-points-in-python
# or else pandas' built-in rolling_mean
# http://pandas.pydata.org/pandas-docs/stable/computation.html#moving-rolling-statistics-moments
def smooth(a,factor):
    k = np.zeros(len(a))
    for i in range(factor):
        k += np.roll(a,i)

    k = k / factor

    #TODO: need to trim the outsides

    return k[factor:-factor]
