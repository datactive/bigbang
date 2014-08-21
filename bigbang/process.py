import bigbang.graph as graph
from bigbang.parse import get_date
import pandas as pd
import datetime
import numpy as np

import Levenshtein
from functools import partial

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

def minimum_but_not_self(column, dataframe):
  minimum = 100
  for index, value in dataframe[column].iteritems():
    if index == column:
      continue
    if value < minimum:
      minimum = value
  return minimum

simple_lev_distance = Levenshtein.distance

def lev_distance_normalized(a,b):
  stop_characters = '"<>'
  a_normal = a.lower().translate(None, stop_characters)
  b_normal = b.lower().translate(None, stop_characters)
  return Levenshtein.distance(a_normal, b_normal)

def sorted_lev(from_dataframe):
  distancedf = matricize(from_dataframe.columns, lev_distance_normalized)
  df = distancedf.astype(int) # specify that the values in the matrix are integers
  sort_for_this_df = partial(minimum_but_not_self, dataframe=df)
  new_columns = sorted(df.columns, key=sort_for_this_df)
  new_df = df.reindex(index=new_columns, columns=new_columns)
  
  return new_df