"""
This script contains the implementation of the VenueParser class, which is responsible for parsing and preprocessing venue names.

The VenueParser class provides methods for extracting abbreviations from venue names, preprocessing venue names by removing dates, month names, word ordinals, 
and blacklist words, and postprocessing the extracted abbreviations.

The script also includes helper methods for determining if a string represents a journal or conference, getting the venue from a Crossref citation, 
and preprocessing and postprocessing venue names.

Note: This script requires the abbreviation dictionary file to be provided during initialization.

Example usage:
    abbreviation_dict = "abbreviation_dict.pkl"
    parser = VenueParser(abbreviation_dict)
    abbrev = parser.get_abbreviations("Proceedings of the International Conference on Machine Learning", "proceedings international conference machine learning")
    print(abbrev)  # Output: "ICML"
"""

import re
import logging
import pickle


class VenueParser():
    """
    A class for parsing and preprocessing venue names.

    Attributes:
    - abbreviation_dict (dict): A dictionary containing mappings of cleaned venue names to their abbreviations.

    Methods:
    - __init__(abbreviation_dict): Initializes the VenueParser object with the provided abbreviation dictionary.
    - get_abbreviations(string, cleaned_string): Extracts abbreviations from a string and returns the cleaned string.
    - preprocess(string, get_abbrv=True): Preprocesses a string by removing dates, months, word ordinals, and blacklist words.
    - citation_year_crossref(citation): Retrieves the year from a citation dictionary.
    - preprocess_venue(venue, get_abbrv=True): Preprocesses a venue name by removing Latin numbers and applying general preprocessing.
    - postprocess(D): Merges similar venue names in a dictionary and returns the merged dictionary.
    """
    def __init__(self, abbreviation_dict):
        # my regexes
        short_date = r"(?:\b(?<!\d\.)(?:(?:(?:[0123]?[0-9](?:[\.\-\/\~][0123]?[0-9])?(?:[\.\-\/(\s{1,2})]))(?:([0123]?[0-9])[\.\-\/][12][0-9]{3}|(\b(?:[Jj]an(?:uary)?|[Ff]eb(?:ruary)?|[Mm]ar(?:ch)?|[Aa]pr(?:il)?|May|[Jj]un(?:e)?|[Jj]ul(?:y)?|[Aa]ug(?:ust)?|[Ss]ept?(?:ember)?|[Oo]ct(?:ober)?|[Nn]ov(?:ember)?|[Dd]ec(?:ember)?)\b)([\.\-\/(\s{1,2})][12][0-9]{3})?))|(?:[0123]?[0-9][\.\-\/][0123]?[0-9][\.\-\/][12]?[0-9]{2,3}))(?!\.\d)\b)"
        self.date_fallback = r"(?:(?:\b(?!\d\.)(?:(?:([0123]?[0-9])(?:(?:st|nd|rd|n?th)?\s?(\b(?:[Jj]an[.]?(?:uary)?|[Ff]eb[.]?(?:ruary)?|[Mm]ar[.]?(?:ch)?|[Aa]pr[.]?(?:il)?|May|[Jj]un[.]?(?:e)?|[Jj]ul[.]?(?:y)?|[Aa]ug[.]?(?:ust)?|[Ss]ept[.]??(?:ember)?|[Oo]ct[.]?(?:ober)?|[Nn]ov[.]?(?:ember)?|[Dd]ec[.]?(?:ember)?))?\s?[\.\-\/\~]\s?)([0123]?[0-9])(?:st|nd|rd|n?th)?(?:[\.\-\/(\s{1,2})])\s?(?:(\b(?:[Jj]an[.]?(?:uary)?|[Ff]eb[.]?(?:ruary)?|[Mm]ar[.]?(?:ch)?|[Aa]pr[.]?(?:il)?|May|[Jj]un[.]?(?:e)?|[Jj]ul[.]?(?:y)?|[Aa]ug[.]?(?:ust)?|[Ss]ept[.]??(?:ember)?|[Oo]ct[.]?(?:ober)?|[Nn]ov[.]?(?:ember)?|[Dd]ec[.]?(?:ember)?))\s?([1-3][0-9]{3})?\b)(?!\.\d)\b)))|(?:(\b(?:[Jj]an(?:uary)?|[Ff]eb(?:ruary)?|[Mm]ar(?:ch)?|[Aa]pr(?:il)?|May|[Jj]un(?:e)?|[Jj]ul(?:y)?|[Aa]ug(?:ust)?|[Ss]ept?(?:ember)?|[Oo]ct(?:ober)?|[Nn]ov(?:ember)?|[Dd]ec(?:ember)?)\b))(?:\s)([0123]?[0-9])(?:\s?[\.\-\/\~]\s?)([0123]?[0-9]))"
        full_date_parts = [
            # prefix
            r"(?:(?<!:)\b\'?\d{1,4},? ?)",

            # month names
            r"\b(?:[Jj]an(?:uary)?|[Ff]eb(?:ruary)?|[Mm]ar(?:ch)?|[Aa]pr(?:il)?|May|[Jj]un(?:e)?|[Jj]ul(?:y)?|[Aa]ug(?:ust)?|[Ss]ept?(?:ember)?|[Oo]ct(?:ober)?|[Nn]ov(?:ember)?|[Dd]ec(?:ember)?)\b",

            # suffix
            r"(?:(?:,? ?\'?)?\d{1,4}(?:st|nd|rd|n?th)?\b(?:[,\/]? ?\'?\d{2,4}[a-zA-Z]*)?(?: ?- ?\d{2,4}[a-zA-Z]*)?(?!:\d{1,4})\b)",
        ]
        __fd1 = "(?:{})".format("".join(
            [full_date_parts[0] + "?", full_date_parts[1], full_date_parts[2]]))
        __fd2 = "(?:{})".format("".join(
            [full_date_parts[0], full_date_parts[1], full_date_parts[2] + "?"]))

        self.date = "(?:" + "(?:" + __fd1 + "|" + __fd2 + ")" + "|" + short_date + ")"
        self.months_regex = r'\b(?:[Jj]an(?:uary)?|[Ff]eb(?:ruary)?|[Mm]ar(?:ch)?|[Aa]pr(?:il)?|May|[Jj]un(?:e)?|[Jj]ul(?:y)?|[Aa]ug(?:ust)?|[Ss]ept?(?:ember)?|[Oo]ct(?:ober)?|[Nn]ov(?:ember)?|[Dd]ec(?:ember)?)\b'
        self.blacklist_words = r'(?i)(day|invited talks|oral session|speech given|posters|volume|issue)'
        self.word_ordinals = r'(?i)(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth)'
        self.space_between_chars = r'([^\w\s\\.,]|_)'
        self.days_abbrev = ['mon', 'tue', 'thu', 'wed', 'fri', 'sat', 'sun']

        with open(abbreviation_dict, 'rb') as fin:
            self.abbreviation_dict = pickle.load(fin)

        self.abbreviation_dict["meeting of the association for computational linguistics"] = "acl"

    def get_abbreviations(self, string, cleaned_string):
        """
        Extracts abbreviations from a given string and removes them from the cleaned string.

        Args:
            string (str): The original string from which to extract abbreviations.
            cleaned_string (str): The cleaned string from which to remove the extracted abbreviations.

        Returns:
            str or None: The extracted abbreviation if found, or None if no abbreviation is found or if the extracted abbreviation is invalid.
        """
        if '(' not in string or ')' not in string:
            if re.search(r'(?:[\-]\s+)([A-Z]+)\b', string) is None:
                return None
        # for some reason got an attribute error must investigate
        # the error occurs from bad entris at elastic: e.g. jem ) chem (
        try:
            abbrev = re.search(r'\((.*?)\)', string).group(1)  # get content of parenthesis
            # remove abbrev from the cleaned_string
            # -------------------------------------
            abbrev_to_remove = '\\b' + re.escape(abbrev).lower() + '\\b'
            cleaned_string = re.sub(abbrev_to_remove, '', cleaned_string)
            cleaned_string = re.sub(' +', ' ', cleaned_string).strip()

            if not cleaned_string or len(cleaned_string) < 3:
                return None
            # -------------------------------------
            # -------------------------------------
        except AttributeError:
            try:
                abbrev = re.search(r'(?:[\-]\s+)([A-Z]+)\b', string).group(1)
            except AttributeError:
                return None
        if not abbrev or len(abbrev) < 3:
            return None
        abbrev = abbrev.lower()
        abbrev = re.sub(r'[^a-z ]+', '', abbrev).strip()
        abbrev = re.sub(' +', ' ', abbrev)
        if not abbrev or len(abbrev) < 3:
            return None
        try:
            firstletters = [s[0] for s in cleaned_string.split(' ')]
        except IndexError:
            firstletters = [cleaned_string[0]]
        prev = "X"
        mismatch = 0
        for _, letter in enumerate(abbrev):
            try:
                index = firstletters.index(letter)
                del firstletters[index]
            except ValueError:
                if prev + letter not in cleaned_string:
                    if mismatch == 1:
                        return None
                    else:
                        mismatch += 1
                else:
                    mismatch -= 1
            finally:
                prev = letter
        return abbrev

    def preprocess(self, string, get_abbrv=True):
        """
        Preprocesses the input string by performing various cleaning operations.

        Args:
            string (str): The input string to be preprocessed.
            get_abbrv (bool, optional): Flag indicating whether to return the abbreviation or the cleaned string. 
                Defaults to True.

        Returns:
            tuple: A tuple containing the preprocessed string and a flag indicating whether an abbreviation was found.
                If `get_abbrv` is False, only the preprocessed string is returned.

        Raises:
            None
        """
        cleaned_string = re.sub(r'\([^)]*\)', '', string)
        cleaned_string = re.sub(self.space_between_chars, ' ', cleaned_string).lower().strip()

        # remove dates
        cleaned_string = re.sub(self.date, '', cleaned_string)
        cleaned_string = re.sub(self.date_fallback, '', cleaned_string)

        cleaned_string = re.sub(r'\b\d{1,4}(?:st|nd|rd|n?th)\b', '', cleaned_string)
        cleaned_string = re.sub(r'[^a-z ]+', '', cleaned_string).strip()

        # remove days, months
        cleaned_string = re.sub(self.months_regex, '', cleaned_string)

        # remove word ordinals and blacklist words
        cleaned_string = re.sub(self.word_ordinals, '', cleaned_string)
        cleaned_string = re.sub(self.blacklist_words, '', cleaned_string)

        # remove extra spaces
        cleaned_string = re.sub(' +', ' ', cleaned_string).strip()

        if not cleaned_string or len(cleaned_string) < 3 or cleaned_string in self.days_abbrev:
            return None, False

        # used for when you just want to preprocess a string
        if not get_abbrv:
            return cleaned_string, False

        # way faster than checking with if
        try:
            return self.abbreviation_dict[cleaned_string], True
        except KeyError:
            abbrev = self.get_abbreviations(string, cleaned_string)
            if abbrev:
                self.abbreviation_dict[cleaned_string] = abbrev
                return abbrev, True
            else:
                return cleaned_string, False

    def preprocess_venue(self, venue, get_abbrv=True):
        """
        Preprocesses the given venue name by removing Latin numbers and applying additional preprocessing steps.

        Args:
            venue (str): The original venue name.
            get_abbrv (bool, optional): Whether to get the abbreviated form of the venue name. Defaults to True.

        Returns:
            str: The preprocessed venue name.

        Raises:
            TypeError: If the venue name is not a string.
        """
        # remove latin numbers
        if venue != 'IV':
            try:
                venue = re.sub(r'\b(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})\b', '', venue)
            except TypeError:
                return None, False

        blacklist = {'n/a', 'na', 'none', '', 'null', 'otherdata', 'nodata', 'unknown', '', None, 'author', 'crossref',
                     'arxiv', 'Crossref', 'Arxiv'}
        if venue in blacklist:
            return None, False
        else:
            venue = self.preprocess(venue, get_abbrv)
        return venue

    def postprocess(self, D):
        """
        Postprocesses the given dictionary by merging keys based on the abbreviation dictionary.

        Parameters:
        - D (dict): The input dictionary to be postprocessed.

        Returns:
        - dict: The postprocessed dictionary with merged keys.

        The method iterates over the keys of the input dictionary and checks if each key is present in the abbreviation dictionary.
        If a key is found in the abbreviation dictionary, it merges the corresponding values into a new key and updates the weights accordingly.
        The merged keys are then removed from the dictionary.
        """
        old = D.copy()
        merged = 0
        for k, v in old.items():
            try:
                mapped = self.abbreviation_dict[k]
                merged += 1
                if mapped not in D.keys():
                    D[mapped] = {}
            except KeyError:
                continue
            for neighbor, weight in v.items():
                try:
                    D[mapped][neighbor] += weight
                except KeyError:
                    D[mapped][neighbor] = weight
            del D[k]
        logging.info('postprocessing merged %d keys', merged)
        return D