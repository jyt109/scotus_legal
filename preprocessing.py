__author__ = 'jeffreytang'

import pandas as pd
from pymongo import MongoClient
import os
import re

class Preprocessing(object):

    def __init__(self, metadata_file, oral_argument_folder, dbname='scotus_cases', collectionname='data'):
        self.metadata_file = metadata_file
        self.oral_argument_folder = oral_argument_folder

        # Instantiate Mongo db + collection
        client = MongoClient()
        db = client[dbname]
        self.tab = db[collectionname]
        # Empty table if there is already sth in it
        self.tab.remove({})

        self.metadata = None
        self.intersect_docket_ids = None
        self._assign_variables()


    @staticmethod
    def _preprocess_meta(meta_df):

        # Define unique and non-unique columns
        uniq_cols = ['justice', 'justiceName', 'vote', 'opinion', 'direction',
                     'majority', 'firstAgreement', 'secondAgreement']
        non_uniq_cols = meta_df.columns.difference(uniq_cols)

        # Method to turn columns to a flat list
        def collapse_to_lst(df, colname):
            return df[colname].tolist()

        # Make justice related columns into flat lists
        collapsed_df_lst = []
        for name, df in meta_df.groupby('docket'):
            #
            info_dict = df[non_uniq_cols].iloc[0].to_dict()
            #
            for jcol in uniq_cols:
                info_dict[jcol] = collapse_to_lst(df, jcol)
            collapsed_df_lst.append(info_dict)

        df = pd.DataFrame(collapsed_df_lst)
        df['_id'] = df['docket']
        return df

    def _read_metadata(self):
        """
        Read in the metadata CSV file
        """
        raw_metadata = pd.read_csv(self.metadata_file)
        # Only interested in cases after 2000 (since oral arguments starts there
        self.metadata = self._preprocess_meta(raw_metadata[raw_metadata['term'] > 2000])

    def _get_oral_filename(self):
        """
        Get all the filenames of the oral args (which contains docket ids)
        """
        return [fname for fname in os.listdir(self.oral_argument_folder)]

    def _get_intersect_docket_ids(self):
        oral_filename = self._get_oral_filename()
        oral_docket_ids = [oral_fname.strip('.txt') for oral_fname in oral_filename]
        meta_docket_ids = self.metadata['docket'].unique().tolist()
        self.intersect_docket_ids = list(set(oral_docket_ids).intersection(set(meta_docket_ids)))

    def _assign_variables(self):
        self._read_metadata()
        self._get_oral_filename()
        self._get_intersect_docket_ids()

    @staticmethod
    def _to_utf8(s):
        if type(s) != str:
            s = str(s)
        return re.sub('[^0-9a-zA-Z \.\,\:\!\'\"]+', ' ', s)

    def insert_intersect_docket_meta_oral(self):
        for i, docket in enumerate(self.intersect_docket_ids):

            if i % 100 == 0:
                print 'Done %s th doc...' % i

            # Get the corresponding metadata based on docket
            meta_dict = self.metadata[self.metadata['docket'] == docket].iloc[0].to_dict()

            # Get the oral arugment text file and put it into meta_dict
            oral_fpath = os.path.join(self.oral_argument_folder, docket + '.txt')
            meta_dict['oral_text'] = open(oral_fpath).read()

            # for loop to make sure every value in dict is utf-8
            meta_dict = {k: self._to_utf8(v) for k, v in meta_dict.iteritems()}

            # Insert into Mongo
            self.tab.insert(meta_dict)

if __name__ == '__main__':
    obj = Preprocessing('metadata.csv', 'oral_arguments')
    # Insert data into Mongo
    obj.insert_intersect_docket_meta_oral()
