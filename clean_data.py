import pandas as pd
import re

class Clean_Data(object):

    def __init__(self, docket, oral_text):
        self.docket = docket
        self.oral_text = oral_text
        self.oral_text_start = None
        self.oral_text_end = None
        self.count_problems = 0
        self.potential_lawyers = None
        self.lawyer_names_lst = []
        self.lawyer_names_dict = {}

    def replace_strings(self):
        """
        Remove extraneous words & phrases from text
        """
        replace_strings = ["ALDERSON REPORTING COMPANY, INC.",
                           "1111 FOURTEENTH STREET, N.W.",
                           "SUITE 400",
                           "WASHINGTON, D.C. 20005",
                           "(202)289-2260",
                           "(800) FOR DEPO",
                           "800-FOR-DEPO",
                           "Alderson Reporting Company",
                           "Official",
                           ]

        for s in replace_strings:
            self.oral_text = self.oral_text.replace(s, '')

    def remove_extra_whitespace(self):
        """
        Remove the large number of repetitive spaces from text
        """
        self.oral_text = " ".join(self.oral_text.split())

    def perform_regex(self):
        """
        Perform regex to remove unnecessary numbers from the text
        """
        self.oral_text = re.sub(r'\s\d+', '', self.oral_text)

    def find_beginning_of_oral_argument(self):
        """
        Identify the beginning of the text of the actual oral argument
        """
        self.oral_text_start = self.oral_text.find('PROCEEDING')

        if self.oral_text_start == -1:
            self.oral_text_start = self.oral_text.find('P ROCEEDING')
        if self.oral_text_start == -1:
            self.oral_text_start = self.oral_text.find('PR OCEEDING')
        if self.oral_text_start == -1:
            self.oral_text_start = self.oral_text.find('PRO CEEDING')
        if self.oral_text_start == -1:
            self.oral_text_start = self.oral_text.find('R O C E E D I')
        if self.oral_text_start == -1:
            self.oral_text_start = self.oral_text.find('PROCEDINGS')
        if self.oral_text_start == -1:
            self.oral_text_start = self.oral_text.find(' OCEEDINGS')
        if self.oral_text_start == -1:
            self.oral_text_start = self.oral_text.find('above-entitled matter came on for oral')
        if self.oral_text_start == -1:
            self.oral_text_start = self.oral_text.find('The above-entitled argument before the Supreme')

        if self.oral_text_start == -1:
            print self.docket, self.oral_text_start, " -- CANNOT FIND START OF ORAL ARGUMENT"


    def find_end_of_oral_argument(self):
        """
        Identify the end of the text of the actual oral argument
        """

        self.oral_text_end = self.oral_text.find('above-entitled matter was submitted.')
    
        if self.oral_text_end == -1:
            self.oral_text_end = self.oral_text.find('case is submitted.')
        if self.oral_text_end == -1:
            self.oral_text_end = self.oral_text.find('case is now submitted.')
        if self.oral_text_end == -1:
            self.oral_text_end = self.oral_text.find('above- entitled matter was submitted.')

        if (self.oral_text_start == -1) or (self.oral_text_end == -1):
            print self.docket, self.oral_text_start, self.oral_text_end, " -- CANNOT FIND START AND/OR END OF ORAL ARGUMENT"

    def identify_lawyers_as_petitioner_respondent(self):
        """
        Identify the names of the lawyers and then classify them as representing either
        the petitioner or the respondent
        """
        count = 0
        petitioner_count = 0
        respondent_count = 0
        slce = slice(self.oral_text_start, self.oral_text_end)

        potential_lawyers_1 = re.findall('ORAL ARGUMENT OF (.+?):', self.oral_text[slce])
        # The one below is good except no way to find petitioner respondent.
        # potential_lawyers_2 = re.findall('ORAL ARGUMENT OF (.+?) ON BEHALF     OF', self.oral_text[slce])

        for line in potential_lawyers_1:
            last_name = line.split()[-1]
            if 'PETITIONER' in line:
                self.lawyer_names_lst.append(('PETITIONER', last_name))
                self.lawyer_names_dict[last_name] = 'PETITIONER'
                petitioner_count += 1
            if 'RESPONDENT' in line:
                self.lawyer_names_lst.append(('RESPONDENT', last_name))
                self.lawyer_names_dict[last_name] = 'RESPONDENT'
                respondent_count += 1

        if (petitioner_count == 0) or (respondent_count == 0):
            # print
            # print self.lawyer_names_lst
            # print self.potential_lawyers
            self.count_problems += 1

    def update_class_variables(self):
        """
        Execute the functions of this class
        """

        self.replace_strings()
        self.remove_extra_whitespace()
        self.perform_regex()
        self.find_beginning_of_oral_argument()
        self.find_end_of_oral_argument()
        self.identify_lawyers_as_petitioner_respondent()
