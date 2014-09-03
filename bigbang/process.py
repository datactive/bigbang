from bigbang.parse import get_date
import pandas as pd
import datetime
import numpy as np
#import math
import pytz
#import pickle
#import os

import Levenshtein
from functools import partial

# turn a list of parsed messages into
# a dataframe of message data, indexed
# by message-id, with column-names from
# headers
def messages_to_dataframe(messages):
    # extract data into a list of tuples -- records -- with
    # the Message-ID separated out as an index 
    pm = [(m.get('Message-ID'), 
           (m.get('From'),
            m.get('Subject'),
            get_date(m),
            m.get('In-Reply-To'),
            m.get('References'),
            m.get_payload()))
          for m in messages if m.get('Message-ID')]

    ids,records = zip(*pm)

    mdf = pd.DataFrame.from_records(list(records),
                                    index=list(ids),
                                    columns=['From',
                                             'Subject',
                                             'Date',
                                             'In-Reply-To',
                                             'References',
                                             'Body'])
    mdf.index.name = 'Message-ID'
                              
    return mdf


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

def activity(messages,clean=True):
    mdf = messages_to_dataframe(messages)

    if clean:
        #unnecessary?
        mdf = mdf.dropna(subset=['Date'])
        mdf = mdf[mdf['Date'] <  datetime.datetime.now(pytz.utc)] # drop messages apparently in the future

    mdf2 = mdf[['From','Date']]
    mdf2['Date'] = mdf['Date'].apply(lambda x: x.toordinal())

    activity = mdf2.groupby(['From','Date']).size().unstack('From').fillna(0)

    new_date_range = np.arange(mdf2['Date'].min(),mdf2['Date'].max())
    #activity.set_index('Date')
    
    activity = activity.reindex(new_date_range,fill_value=0)

    return activity

# takes a DataFrame in the format returned by activity
# takes a list of tuples of format ('from 1', 'from 2') to consolidate
# returns the consolidated DataFrame (a copy, not in place)
def consolidate_senders_activity(activity_df, to_consolidate):
  df = activity_df.copy(deep=True)
  for consolidate in to_consolidate:
    column_a, column_b = consolidate
    if column_a in df.columns and column_b in df.columns:
      df[column_a] = df[column_a] + df[column_b]
      df.drop(column_b, inplace=True, axis=1) # delete the second column
  return df


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

# create a matrix by applying func to pairwise combinations of elements in a Series
# returns a square matrix as a DataFrame
# should return a symmetric matrix if func(a,b) == func(b,a)
# should return the identity matrix if func == '=='
def matricize(series, func):
  matrix = pd.DataFrame(columns=series, index=series)
  for index, element in enumerate(series):
    for second_index, second_element in enumerate(series):
      matrix.iloc[index,second_index] = func(element, second_element)
  
  return matrix