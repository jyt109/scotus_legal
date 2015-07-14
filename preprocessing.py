import pandas as pd
from pymongo import MongoClient
import os
import re
import clean_data
import interruptions
import sentiment

class Preprocessing(object):

    def __init__(self, metadata_file, oral_argument_folder, dbname='scotus_cases', collectionname='data'):
        self.metadata_file = metadata_file
        self.oral_argument_folder = oral_argument_folder

        # Instantiate Mongo db + collection
        client = MongoClient()
        db = client[dbname]
        self.tab = db[collectionname]
        # Empty table if it already exists
        self.tab.remove({})

        self.metadata = None
        self.intersect_docket_ids = None
        self._assign_variables()


    @staticmethod
    def _preprocess_meta(meta_df):
        """
        Preprocess metadata_file
        Collapse rows so that there is only one row per docket
            Each docket has nine rows for each justice
            Take justice-relevant information in each of nine rows and combine
            Unique cols = Justice-relevant information
        :param meta_df:
        :return: df
        """
        # Define unique and non-unique columns
        uniq_cols = ['justice', 'justiceName', 'vote', 'opinion', 'direction',
                     'majority', 'firstAgreement', 'secondAgreement']
        non_uniq_cols = meta_df.columns.diff(uniq_cols)

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
        Updates self.metadata
        """
        raw_metadata = pd.read_csv(self.metadata_file)
        # Only interested in cases after 2000 (since oral arguments starts there
        self.metadata = self._preprocess_meta(raw_metadata[raw_metadata['term'] >= 2000])

    def _get_oral_filename(self):
        """
        Returns all the filenames of the oral args (which contains docket ids)
        """
        return [fname for fname in os.listdir(self.oral_argument_folder)]
        
    def _get_intersect_docket_ids(self):
        """
        Not all cases the SCOTUS hears have an oral argument hearing.
        Match the metadata cases (all cases) against the oral argument cases.
        Oral arguments should be a subset of the metadata cases
        Updates self.intersect_docket_ids
        """
        oral_filename = self._get_oral_filename()
        oral_docket_ids = [oral_fname.strip('.txt') for oral_fname in oral_filename]
        meta_docket_ids = self.metadata['docket'].unique().tolist()
        self.intersect_docket_ids = list(set(oral_docket_ids).intersection(set(meta_docket_ids)))

    def _assign_variables(self):
        """
        This function calls the three functions to update class attributes
        """
        self._read_metadata()
        self._get_oral_filename()
        self._get_intersect_docket_ids()

    @staticmethod
    def _to_utf8(s):
        """
        Returns text that has regex performed
        """
        if type(s) != str:
            s = str(s)
        return re.sub('[^0-9a-zA-Z \.\,\:\!\'\"\-]+', ' ', s)

    def insert_intersect_docket_meta_oral(self):
        """
        For each docket, get corresponding metadata and oral argument text and add to
        mongodb collection
        :return:
        """
        count_problems = 0

        for i, docket in enumerate(self.intersect_docket_ids):

            if i % 100 == 0:
                print 'Done %s th doc...' % i

            # Get the corresponding metadata based on docket
            meta_dict = self.metadata[self.metadata['docket'] == docket].iloc[0].to_dict()

            # Get the oral argument text file and put it into meta_dict
            oral_fpath = os.path.join(self.oral_argument_folder, docket + '.txt')
            meta_dict['oral_text'] = open(oral_fpath).read()

            # for loop to make sure every value in dict is utf-8
            meta_dict = {k: self._to_utf8(v) for k, v in meta_dict.iteritems()}

            clean_data_obj = clean_data.Clean_Data(docket, meta_dict['oral_text'])
            clean_data_obj.update_class_variables()
            count_problems += clean_data_obj.count_problems

            # Add output from clean_data_obj to meta_dict
            meta_dict['oral_text'] = clean_data_obj.oral_text
            meta_dict['oral_text_start'] = clean_data_obj.oral_text_start
            meta_dict['oral_text_end'] = clean_data_obj.oral_text_end            
            meta_dict['potential_lawyers'] = clean_data_obj.potential_lawyers
            meta_dict['lawyer_names_lst'] = clean_data_obj.lawyer_names_lst

            # Instantiate interruptions.py
            interruptions_obj = interruptions.Interruptions(docket, 
                                                            clean_data_obj.oral_text,
                                                            clean_data_obj.oral_text_start,
                                                            clean_data_obj.oral_text_end,
                                                            clean_data_obj.lawyer_names_dict)
            interruptions_obj.update_class_variables()

            # Add output from interruptions.py
            meta_dict['statements'] = interruptions_obj.statements
            meta_dict['interruptions_dict'] = interruptions_obj.interruptions_dict
            meta_dict['interruptions_side_dict'] = interruptions_obj.interruptions_side_dict

            if 'MR.GARRE' in interruptions_obj.interruptions_dict:
                print 'interruptions_dict', interruptions_obj.docket
            if 'MR.GARRE' in interruptions_obj.interruptions_side_dict:
                print 'interruptions_dict', interruptions_obj.docket

            # Instantiate sentiment_obj.py
            sentiment_obj = sentiment.Sentiment(docket, interruptions_obj.statements)
            sentiment_obj.update_class_variables()

            # Add output from sentiment.py
            meta_dict['sentiment_dict'] = sentiment_obj.sentiment_dict

            if 'MR.GARRE' in sentiment_obj.sentiment_dict:
                print 'sentiment_dict', sentiment_obj.docket

            if i % 100 == 0:
                # print docket, clean_data_obj.oral_text_start
                print '# of problems: ', count_problems

            # Insert into Mongo
            self.tab.insert(meta_dict)

if __name__ == '__main__':
    oral_arguments = '/Users/nojzachariah/scotus_oral_arguments/data/z02_converted_pdfs_to_text/'
    obj = Preprocessing('SCDB_2014_01_justiceCentered_Citation.csv', oral_arguments)
    # Insert data into Mongo
    obj.insert_intersect_docket_meta_oral()
