from bigbang.parse import get_date
import datetime
import numpy as np
import pandas as pd
import pytz


def load(path):
    data = pd.read_csv(path)
    return Archive(data)

class Archive:
    """
    A representation of a mailing list archive.
    """

    data = None
    activity = None

    def __init__(self, data):
        if type(data) is list:
            self.data = self.messages_to_dataframe(data)
        elif type(date) is pandas.core.frame.DataFrame:
            self.data = data
        elif type(data) is str:
            ## should this laod from path or collect from web?
            ## or check one and do the other if not available?
            print "TODO: Implement initialization from string"

    # turn a list of parsed messages into
    # a dataframe of message data, indexed
    # by message-id, with column-names from
    # headers
    def messages_to_dataframe(self,messages):
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

    def get_activity(self):
        if self.activity is None:
            self.activity = self.compute_activity(self)

        return self.activity

    def compute_activity(self,clean=True):
        mdf = self.data

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

    def save(self,path):
        self.data.to_csv(path,",")
