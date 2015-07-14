import re
from collections import defaultdict, Counter, deque

class Interruptions(object):
    """
    Objective: Count the number of times each side (Petitioner or Respondent) is interrupted

    Potential ways to identify interruptions:
        - Find '--'
        - Find speech text where '--' which is the last thing
        - Identify speech text

    Methodology:
        - Identify speakers (DONE)
            Find words that end with ':' and are all caps
        - Identify speech text
            - Language between speakers (Not perfect)
        - Identify speech text that ends with interruptions
    """
    def __init__(self, docket, oral_text, oral_text_start, oral_text_end, lawyer_names_dict):
        self.docket = docket
        self.oral_text = oral_text
        self.oral_text_start = oral_text_start
        self.oral_text_end = oral_text_end
        self.lawyer_names_dict = lawyer_names_dict
        self.oral_text_slce = slice(oral_text_start, oral_text_end)
        self.oral_text_targeted = self.oral_text[self.oral_text_slce]
        self.speaker_number_of_statements_dict = None
        self.speaker_start_position_dict = {}
        self.statements = []
        self.interruptions_dict = Counter()
        self.interruptions_side_dict = Counter()
        self.not_lawyer_names = set()
        self.justice_name = ['QUESTION', 'SCALIA', 'ROBERTS',
                            'SOTOMAYOR', 'GINSBURG', 'KENNEDY',
                            'SOUTER', 'BREYER', 'ALITO',
                            'STEVENS', 'KAGAN', 'THOMAS',
                            "O'CONNOR", 'REHNQUIST']

    def identify_speakers(self):
        """
        Identify the speakers during oral arguments.
        Results should look like "<name>:"
        """
        speaker_lst = re.findall('[A-Z]+:', self.oral_text_targeted)
        self.speaker_number_of_statements_dict = Counter()

        for name in speaker_lst:
            self.speaker_number_of_statements_dict[name] += 1

        self.speaker_number_of_statements_dict = \
            {key: value for key, value in self.speaker_number_of_statements_dict.items() if value > 1}

    def locate_colons(self):
        """
        Identify locations of colons (because statements begin with <name>:)
        """
        return [colon.start() for colon in re.finditer(':', self.oral_text_targeted)]

    def identify_name_before_colon(self, colon_location_lst):
        """
        Assuming statements begin with "<name>:", find the starting position of the word immediately
        prior to the colon
        """
        name_start_lst = []

        for end in colon_location_lst:
            start = end - 30
            slce = slice(start, end)
            last_word = self.oral_text_targeted[slce].rsplit(None, 1)[-1:]
            last_word = str(last_word)[2:-2]
            start = end - len(last_word)
            name_start_lst.append(start)

        return name_start_lst

    def identify_beg_end_of_statements(self, name_start_lst):
        """
        Create two lists.
        One list has the starting position of each statement.
        The other list has the ending position of each statement. 
        """
        statement_end_lst = deque(name_start_lst)
        statement_start_lst = deque(name_start_lst)

        # name_start_lst has starting point for each phrase so add 0
        statement_start_lst.appendleft(0)
        # name_end_lst has ending point for each phrase so add the last point
        statement_end_lst.append(len(self.oral_text_targeted))

        return statement_start_lst, statement_end_lst

    def capture_statements(self, statement_start_lst, statement_end_lst):
        """
        Capture each oral statement.
        Remove extraneous words from the end of each statement.
        """
        for statement_beg, statement_end in zip(statement_start_lst, statement_end_lst):
            slce = slice(statement_beg, statement_end)
            statement_tmp = self.oral_text_targeted[slce]

            if (len(statement_tmp.split()) > 2) and (not (statement_tmp.isupper())):
                while statement_tmp.rsplit(None, 1)[-1].isupper():
                    statement_tmp = statement_tmp.rsplit(' ', 1)[0]
                self.statements.append(statement_tmp)

    def identify_statements(self):
        """
        This function identifies, captures, and stores each oral statement
        """
        #Identify locations of colons (because statements begin with <name>:)
        name_end_lst = self.locate_colons()

        # Identify the word (name) immediately before the colon
        name_start_lst = self.identify_name_before_colon(name_end_lst)

        # Identity the start and end 
        statement_start_lst, statement_end_lst = self.identify_beg_end_of_statements(name_start_lst)

        # Capture each statement
        self.capture_statements(statement_start_lst, statement_end_lst)

    def classify_statements(self):
        """
        This function identifies the starting position of each speakers statements.
        Not currently used.
        """
        for speaker, count in self.speaker_number_of_statements_dict.iteritems():
            speaker_start_position_lst = [statement.start() for statement in re.finditer(speaker, self.oral_text_targeted)]
            self.speaker_start_position_dict[speaker] = speaker_start_position_lst

    def update_lawyer_names_dict(self, name):
        if name in self.lawyer_names_dict:
            if self.lawyer_names_dict[name] == 'PETITIONER':
                self.interruptions_side_dict['PETITIONER'] += 1
            if self.lawyer_names_dict[name] == 'RESPONDENT':
                self.interruptions_side_dict['RESPONDENT'] += 1
        else:
            if name not in self.justice_name:
                self.not_lawyer_names.add(name)

        ### Identify the words that are not counted as lawyer names (in case not accurate)
        # if len(self.not_lawyer_names) > 0:
            # print
            # print self.docket
            # print "Here are the names in the lawyer_names_dict:"
            # for i in self.lawyer_names_dict:
            #     print i, self.lawyer_names_dict[i]
            # print 'Not a lawyer name (not included above): ', self.not_lawyer_names

    def identify_interruptions(self):
        for statement in self.statements:
            potential_interruption = statement.rsplit(' ', 1)
            if len(potential_interruption) > 1:
                if (potential_interruption[-1] == '--'):
                    name = statement.split(':', 1)[0]
                    if (len(name.split()) == 1) and name.isupper():
                        # Some names do not have a space between titles (MR.,MS.) and name
                        # so removing the title. MongoDB does not like '.'s in keys of dictionaries
                        name = name.rstrip(' ')
                        name = name.rstrip('.')
                        if '.' in name:
                            name = name.split('.', 1)[-1]
                        self.interruptions_dict[name] += 1
                        self.update_lawyer_names_dict(name)

        ### Verify that interruptions are being counted
        # print self.docket
        # print "Number of interruptions (Pet): ", self.interruptions_side_dict['PETITIONER']
        # print "Number of interruptions (Res): ", self.interruptions_side_dict['RESPONDENT']

    def update_class_variables(self):
        self.identify_speakers()
        self.identify_statements()
        # self.classify_statements()
        self.identify_interruptions()