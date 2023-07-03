import json
import os.path
import ssl
from urllib import request
from datetime import datetime
import re


class DateInfo:
    def __init__(self, dt: datetime):
        """
        Initialize DateInfo object with a datetime object.

        Args:
            dt (datetime): The datetime object.

        Attributes:
            datetime (datetime): The datetime object.
            is_work (bool): Flag indicating if the date is a workday.
            is_short (bool): Flag indicating if the date is a short workday.
            is_holiday (bool): Flag indicating if the date is a holiday.
            is_weekend (bool): Flag indicating if the date is a weekend.
        """
        self.datetime = dt
        self.is_work = False
        self.is_short = False
        self.is_holiday = False
        self.is_weekend = False


class ProcessCalendar:
    def __init__(self):
        """
        Initialize ProcessCalendar object.

        Attributes:
            cache_name (str): The name of the cache file.
            _url_template (str): The URL template for fetching calendar data.
            _table_pattern (re.Pattern): Regular expression pattern for extracting calendar table.
            _pre_holiday_pattern (re.Pattern): Regular expression pattern for extracting pre-holiday dates.
            _weekend_pattern (re.Pattern): Regular expression pattern for extracting weekend dates.
            _holiday_pattern (re.Pattern): Regular expression pattern for extracting holiday dates.
            _dict (dict): Dictionary to store calendar data.
        """
        self.cache_name = 'production_calendar_cache.json'
        self._url_template = 'https://www.consultant.ru/law/ref/calendar/proizvodstvennye/'
        self._table_pattern = re.compile(r'<table class="cal">(.*?)</table>', re.DOTALL)
        self._pre_holiday_pattern = re.compile(r'<td class="preholiday">(\d+)<')
        self._weekend_pattern = re.compile(r'<td class="weekend">(.*?)</td>')
        self._holiday_pattern = re.compile(r'<td class="holiday.*?">(.*?)</td>')
        self._dict = dict()

    def __get_html(self, year):
        """
        Fetches HTML content from the URL for a given year.

        Args:
            year (int): The year for which to fetch the HTML content.

        Returns:
            str: The HTML content of the webpage, or None if an error occurred.
        """
        url = f'{self._url_template}{year}/'
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        try:
            response = request.urlopen(url, context=context)
        except Exception as ex:
            print(ex)
            return None

        return response.read().decode('utf-8')

    def __get_year_data(self, year):
        """
        Retrieves calendar data for a given year and stores it in the _dict attribute.

        Args:
            year (int): The year for which to retrieve the calendar data.
        """
        self._dict[year] = dict()
        html = self.__get_html(year)

        if html:
            for month, table in enumerate(self._table_pattern.findall(html)):
                self._dict[year][month + 1] = {
                    'pre_holidays': tuple(map(int, self._pre_holiday_pattern.findall(table))),
                    'weekends': tuple(map(int, self._weekend_pattern.findall(table))),
                    'holidays': tuple(map(int, self._holiday_pattern.findall(table)))
                }

    def date_info(self, dt: datetime) -> DateInfo:
        """
        Retrieves information about a given date.

        Args:
            dt (datetime): The datetime object representing the date.

        Returns:
            DateInfo: An instance of DateInfo containing information about the date.
        """
        date = DateInfo(dt)
        if self._dict.get(dt.year) is None:
            if not self.__read_cache_json(dt.year):
                self.__get_year_data(dt.year)
                self.__write_cache_json()

        if dt.day in self._dict[dt.year][dt.month]['pre_holidays']:
            date.is_work = True
            date.is_short = True
        elif dt.day in self._dict[dt.year][dt.month]['holidays']:
            date.is_holiday = True
            date.is_weekend = True
        elif dt.day in self._dict[dt.year][dt.month]['weekends']:
            date.is_weekend = True
        else:
            date.is_work = True

        return date

    def __write_cache_json(self):
        """
        Writes the calendar data stored in _dict to a JSON cache file.
        If the cache file does not exist, it is created.
        """
        if not os.path.exists(self.cache_name):
            with open(self.cache_name, 'w') as f:
                json.dump(self._dict, f, sort_keys=True)
                return

        with open(self.cache_name, 'r+') as f:
            cache = {int(k): v for k, v in json.load(f).items()}
            f.seek(0)
            cache.update(self._dict)
            json.dump(cache, f, sort_keys=True)
            f.truncate()

    def __read_cache_json(self, year: int) -> bool:
        """
        Reads the calendar data from the JSON cache file for a given year.

        Args:
            year (int): The year for which to read the calendar data.

        Returns:
            bool: True if the calendar data for the year was found in the cache, False otherwise.
        """
        if not os.path.exists(self.cache_name):
            return False

        with open(self.cache_name, 'r') as f:
            data = json.load(f)
            if not data.get(str(year)):
                return False

            self._dict[year] = {int(k): v for k, v in data[str(year)].items()}
        return True

    def pre_cache_json(self, *years: int):
        """
        Pre-caches the calendar data for the specified years.

        Args:
            *years (int): Variable number of years for which to pre-cache the calendar data.
        """
        for year in years:
            self.__get_year_data(year)

        self.__write_cache_json()
