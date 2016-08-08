import datetime
import mailman
import mailbox
import numpy as np
from bigbang.thread import Thread
from bigbang.thread import Node
import bigbang.process as process
import pandas as pd
import pytz
import utils


def load(path):
    data = pd.read_csv(path)
    return Archive(data)


class Archive(object):

    """
    A representation of a mailing list archive.
    """

    data = None
    activity = None
    threads = None
    entities = None

    def __init__(self, data, archive_dir="archives", mbox=False):
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
            self.data = mailman.load_data(data,archive_dir=archive_dir,mbox=mbox)

        self.data['Date'] = pd.to_datetime(self.data['Date'], utc=True)
        self.data.drop_duplicates(inplace=True)

        # Drops any entries with no Date field.
        # It may be wiser to optionally
        # do interpolation here.
        if not self.data['Date'].isnull().any():
            self.data.dropna(subset=['Date'], inplace=True)

        #convert any null fields to None -- csv saves these as nan sometimes
        self.data = self.data.where(pd.notnull(self.data),None)

        try:
            #set the index to be the Message-ID column
            self.data.set_index('Message-ID',inplace=True)
        except KeyError:
            #will get KeyError if Message-ID is already index
            pass

        self.data.sort(columns='Date', inplace=True)

    def resolve_entities(self,inplace=True):
        if self.entities is None:
            if self.activity is None:
                self.get_activity()

            self.entities = process.resolve_sender_entities(self.activity)

        to_replace = []
        value = []

        for e, names in self.entities.items():
            for n in names:
                to_replace.append(n)
                value.append(e)

        data = self.data.replace(to_replace=to_replace,value=value,inplace=inplace)

        # clear and replace activity with resolved activity
        self.activity = None
        self.get_activity()

        if inplace:
            return self.data
        else:
            return data

    def get_activity(self,resolved=False):
        """
        Get the activity matrix of an Archive.
        Columns of the returned DataFrame are the Senders of emails.
        Rows are indexed by ordinal date.
        Cells are the number of emails sent by each sender on each data.

        If *resolved* is true, then default entity resolution is run on the
        activity matrix before it is returned.
        """
        if self.activity is None:
            self.activity = self.compute_activity(self)

        if resolved:
            self.entities = process.resolve_sender_entities(self.activity)
            eact = utils.repartition_dataframe(self.activity,self.entities)
            
            return eact

        return self.activity

    def compute_activity(self, clean=True):
        mdf = self.data

        if clean:
            # unnecessary?
            mdf = mdf.dropna(subset=['Date'])
            mdf = mdf[
                mdf['Date'] < datetime.datetime.now(
                    pytz.utc)]  # drop messages apparently in the future

        mdf2 = mdf.reindex(columns = ['From', 'Date'])
        mdf2['Date'] = mdf['Date'].apply(lambda x: x.toordinal())

        activity = mdf2.groupby(
            ['From', 'Date']).size().unstack('From').fillna(0)

        new_date_range = np.arange(mdf2['Date'].min(), mdf2['Date'].max())
        # activity.set_index('Date')

        activity = activity.reindex(new_date_range, fill_value=0)

        return activity

    def get_threads(self, verbose=False):

        if self.threads is not None:
            return self.threads

        df = self.data

        threads = list()
        visited = dict()

        total = df.shape[0]
        c = 0

        for i in df.iterrows():

            if verbose:
                c += 1
                if c % 1000 == 0:
                    print "Processed %d of %d" %(c,total)

            if(i[1]['In-Reply-To'] is None):
                root = Node(i[0], i[1])
                visited[i[0]] = root
                threads.append(Thread(root))
            elif(i[1]['In-Reply-To'] not in visited.keys()):
                root = Node(i[1]['In-Reply-To'])
                succ = Node(i[0],i[1], root)
                root.add_successor(succ)
                visited[i[1]['In-Reply-To']] = root
                visited[i[0]] = succ
                threads.append(Thread(root, known_root=False))
            else:
                parent = visited[i[1]['In-Reply-To']]
                node = Node(i[0],i[1], parent)
                parent.add_successor(node)
                visited[i[0]] = node

        self.threads = threads

        return threads

    def save(self, path,encoding='utf-8'):
        self.data.to_csv(path, ",",encoding=encoding)


def find_footer(messages,number=1):
    '''
    Returns the footer of a DataFrame of emails.
    A footer is a string occurring at the tail of most messages.
    Messages can be a DataFrame or a Series
    '''
    if isinstance(messages,pd.DataFrame):
        messages = messages['Body']

    # sort in lexical order of reverse strings to maximize foot length
    srb = messages.apply(lambda x: None if x is None else x[::-1]).order()
    #srb = df.apply(lambda x: None if x['Body'] is None else x['Body'][::-1],
    #              axis=1).order()
    # begin walking down the series looking for maximal overlap
    counts = {}

    last = None
    last_i = None
    current = None

    def clean_footer(foot):
        return foot.strip()

    for b in srb:
        if last is None:
            last = b
            continue
        elif b is None:
            continue
        else:
            head,i = utils.get_common_head(b,last,delimiter='\n')
            head = clean_footer(head[::-1])
            last = b

            if head in counts:
                counts[head] = counts[head] + 1
            else:
                counts[head] = 1

        last = b

    # reduce candidates that are strictly longer and less frequent
    # than most promising footer candidates
    for n,foot1 in sorted([(v,k) for k,v in counts.items()],reverse=True):
        for foot2, m in counts.items():
            if n > m and foot1 in foot2 and len(foot1) > 0:
                counts[foot1] = counts[foot1] + counts[foot2]
                del counts[foot2]

    candidates = sorted([(v,k) for k,v in counts.items()],reverse=True)

    return candidates[0:number]
