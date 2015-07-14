import re
from collections import defaultdict
from textblob import TextBlob

class Sentiment(object):
    """
    Objective: Calculate the sentiment polarity for each statement and assign to
    Petitioner, Respondent, or Justice (where possible)
    """
    def __init__(self, docket, statements):
        self.docket = docket
        self.statements = statements
        self.sentiment_dict = defaultdict(list)

    def identify_sentiment_lawyers(self):
        for statement in self.statements:
            if len(statement.split(':', 1)) == 2:
                name, statement_text = statement.split(':', 1)
                if (len(name.split()) == 1) and name.isupper():
                    # Some names do not have a space between titles (MR.,MS.) and name
                    # so removing the title. MongoDB does not like '.'s in keys of dictionaries
                    name = name.rstrip(' ')
                    name = name.rstrip('.')
                    if '.' in name:
                        name = name.split('.', 1)[-1]
                    statement_tb = TextBlob(statement_text)
                    self.sentiment_dict[name].append(statement_tb.sentiment.polarity)

        ### Print out examples for review
        # print '#'*30
        # print self.docket
        # for name, lst in self.sentiment_dict.iteritems():
        #     print name, lst
        #     print

        ### Verify that sentiment is being calculated and averaged
        # print self.docket
        # print "Number of interruptions (Pet): ", self.interruptions_side_dict['PETITIONER']
        # print "Number of interruptions (Res): ", self.interruptions_side_dict['RESPONDENT']
            
    def update_class_variables(self):
        self.identify_sentiment_lawyers()