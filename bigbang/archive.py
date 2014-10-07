from bigbang.parse import get_date
import datetime
import mailman
import mailbox
import numpy as np
import pandas as pd
import pytz


def load(path):
    data = pd.read_csv(path)
    return Archive(data)

class MissingDataException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Archive:
    """
    A representation of a mailing list archive.
    """

    data = None
    activity = None

    def __init__(self, data,archive_dir="archives",single_file=False):
        """
        Initializes an Archive object.

        The behavior of the constructor depends on the type
        of its first argument, data.

        If data is a list, then it is treated as am iterator of messages,
        as parsed by the mailman.mbox class in the Python standard library.

        If data is a Pandas DataFrame, it is treated as a representation of
        email messages with columns for Message-ID, From, Date, In-Reply-To,
        References, and Body. The created Archive becomes a wrapper around a
        copy of the input DataFrame.

        If data is a string, then it is interpreted as a path to either a
        single .mbox file (if the optional argument single_file is True) or else
        to a directory of .mbox files (also in .mbox format). Note that the
        file extensions need not be .mbox; frequently they will be .txt. 
        """
        if type(data) is list:
            self.data = self.messages_to_dataframe(data)
        elif type(data) is pd.core.frame.DataFrame:
            self.data = data.copy()
        elif type(data) is str:
            messages = None

            if single_file:
                # treat string as the path to a file that is an mbox
                box = mailbox.mbox(data, create=False)
                messages = box.values()
            else:
                # assume string is the path to a directory with many  
                messages = mailman.open_list_archives(data,base_arc_dir=archive_dir)

                if len(messages) == 0:
                    raise MissingDataException("No messages in %s under %s. Did you run the collect_mail.py script?" % (archive_dir,data))

            self.data= self.messages_to_dataframe(messages)

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
