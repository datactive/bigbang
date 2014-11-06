import datetime
import mailman
import mailbox
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

    def __init__(self, data, archive_dir="archives", single_file=False):
        """
        Initializes an Archive object.

        The behavior of the constructor depends on the type
        of its first argument, data.

        If data is a Pandas DataFrame, it is treated as a representation of
        email messages with columns for Message-ID, From, Date, In-Reply-To,
        References, and Body. The created Archive becomes a wrapper around a
        copy of the input DataFrame.

        If data is a string, then it is interpreted as a path to either a
        single .mbox file (if the optional argument single_file is True) or
        else to a directory of .mbox files (also in .mbox format). Note that
        the file extensions need not be .mbox; frequently they will be .txt.

        Upon initialization, the Archive object drops duplicate entries
        and sorts its member variable *data* by Date.
        """

        if isinstance(data, pd.core.frame.DataFrame):
            self.data = data.copy()
        elif isinstance(data, str):

            self.data = mailman.load_data(data,archive_dir=archive_dir)

            self.data['Date'] = pd.to_datetime(self.data['Date'], utc=True)

            self.data.drop_duplicates(inplace=True)

            # Drops any entries with no Date field.
            # It may be wiser to optionally
            # do interpolation here.
            self.data.dropna(subset=['Date'], inplace=True)

            self.data.sort(columns='Date', inplace=True)

            """
    # turn a list of parsed messages into
    # a dataframe of message data, indexed
    # by message-id, with column-names from
    # headers
    def messages_to_dataframe(self, messages):
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

        ids, records = zip(*pm)

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
            """

    def get_activity(self):
        if self.activity is None:
            self.activity = self.compute_activity(self)

        return self.activity

    def compute_activity(self, clean=True):
        mdf = self.data

        if clean:
            # unnecessary?
            mdf = mdf.dropna(subset=['Date'])
            mdf = mdf[
                mdf['Date'] < datetime.datetime.now(
                    pytz.utc)]  # drop messages apparently in the future

        mdf2 = mdf[['From', 'Date']]
        mdf2['Date'] = mdf['Date'].apply(lambda x: x.toordinal())

        activity = mdf2.groupby(
            ['From', 'Date']).size().unstack('From').fillna(0)

        new_date_range = np.arange(mdf2['Date'].min(), mdf2['Date'].max())
        # activity.set_index('Date')

        activity = activity.reindex(new_date_range, fill_value=0)

        return activity

    def save(self, path):
        self.data.to_csv(path, ",")
