"""
This file contains a class that can collate multi-axis data from one of 
a set number of TRAC webpages.

There are two kinds of TRAC webpages:
    - link-based tables
    - object-based tables

Of these two kinds, either can have a variant in which year is broken into its
own drop-down menu.
"""

# Browser-agnostic imports
# Note: Browser-specific imports are handled in CollateEngine.get_driver()
from pathlib import Path
import os
from typing import Literal, Optional, get_args
import pandas as pd
from time import sleep
from tqdm import tqdm
import json
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# WEBDRIVER_PATH = None
WEBPAGE_TYPES = {
    'https://trac.syr.edu/phptools/immigration/ntanew/': 'object-whole',
    'https://trac.syr.edu/phptools/immigration/closure/': 'object-whole',
    'https://trac.syr.edu/phptools/immigration/asyfile/': 'object-whole',
    'https://trac.syr.edu/phptools/immigration/asylum/': 'object-whole',
    'https://trac.syr.edu/phptools/immigration/mpp4/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/juvenile/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/mwc/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/cbparrest/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/cbpinadmiss/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/arrest/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/detainhistory/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/remove/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/removehistory/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/secure/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/backlog/': 'object-broken',
    'https://trac.syr.edu/phptools/immigration/addressrep/': 'map-table',
    'https://trac.syr.edu/immigration/reports/judgereports/': 'table-only-1',
    'https://trac.syr.edu/phptools/immigration/asylumbl/': 'object-broken',
    'https://trac.syr.edu/phptools/immigration/bond/': 'table-tab',
    'https://trac.syr.edu/phptools/immigration/detention/': 'link-broken',
    'https://trac.syr.edu/immigration/detentionstats/facilities.html': 'table-only-2',
    'https://trac.syr.edu/immigration/detentionstats/atd_pop_table.html': 'table-only-2'
}

FULLY_SUPPORTED_TYPES = ['object-whole', 'link-whole']
PARTIALLY_SUPPORTED_TYPES = ['object-broken', 'link-broken']

TIMEOUT = 10

SUPPORTED_BROWSERS = Literal['Firefox', 'Chrome', 'Edge', 'Safari']

class DatasetException(Exception):
    def __init__(self, data, current_t1_row, current_t2_row):
        self.data = data
        self.current_t1_row = current_t1_row
        self.current_t2_row = current_t2_row

class Table:
    """A Table is a collection of Rows."""
    def __init__(self, driver, table_index: int, table_type: Literal['object', 'link']):
        # Set initial instance attributes
        self.driver = driver
        self.table_index = table_index
        self.table_type = table_type
       
        # Set private/container instance attributes
        self._web_element = None
        self._text_rows = []
        self._rows = []
        
        # Set instance table query attribute based on the table type
        if table_type == 'object':
            self.table_query = (By.CLASS_NAME, 'table-fixed')
        elif table_type == 'link':
            self.table_query = (By.CLASS_NAME, 'Table')

        # Set instance row query attribute based on the table type
        if self.table_type == 'object':
            self.row_query = (By.CLASS_NAME, 'flex-row')
        elif self.table_type == 'link':
            self.row_query = (By.XPATH, ".//tr")

        # Set instance row clickable element query attribute based on table type
        if self.table_type == 'object':
            self.row_clickable_query = None #because row_query is already clickable
        elif self.table_type == 'link':
            self.row_clickable_query = (By.XPATH, ".//td[@class='Data l']/a")

    @property
    def text_rows(self):
        """
        List of strings representing the useful rows from the table, without
        leading and trailing whitespace, and without headers.
        """
        if self._text_rows == []:
            # Get text, filter for meaninful rows
            def is_meaningful(text):
                return (text != '' and 'All' not in text and 'Total' not in text)
            try:
                self._text_rows = self.web_element.text.split('\n')
            except StaleElementReferenceException:
                self.recalculate_web_element()
                self._text_rows = self.web_element.text.split('\n')
            self._text_rows = [r for r in self._text_rows if is_meaningful(r)]
        return self._text_rows
    
    def recalculate_text_rows(self):
        self._text_rows = []
        self._text_rows = self.text_rows
    
    @property
    def rows(self):
        """
        List of Row objects for the table, of the same length as text_rows.
        """
        # Calculate rows if necessary
        if self._rows == []:
            # In object-type tables, text_rows are currently offset by 4 
            # (1-3 are empty, 4 is header) (NOTE: this could change)
            if self.table_type == 'object':
                self._rows = [Row(self, i+4, self.row_query) for i in range(len(self.text_rows))]
            
            # In link-type tables, text_rows are currently offset by 2 (header) 
            # (NOTE: this could change)
            elif self.table_type == 'link':
                self._rows = [Row(self, i+2, self.row_query) for i in range(len(self.text_rows))]

            # I don't understand why, but sometimes the lengths of text_rows
            # and rows are different. This makes sure they are the same.
            #       TODO: come up with a better fix
            if len(self._rows) > len(self.text_rows):
                for i in range(len(self._rows) - len(self.text_rows)):
                    _ = self._rows.pop(-1)
            
        return self._rows
    
    def recalculate_rows(self):
        self._rows = []
        self._rows = self.rows  # better way to use setter?

    def calculate_all_row_web_elements(self):
        # Calculate rows if necessary
        if self._rows == []:
            self.recalculate_rows()
      
        # Calculate all row elements
        wait = WebDriverWait(self.web_element, TIMEOUT)
        new_row_web_elements = wait.until(EC.presence_of_all_elements_located(self.row_query))

        # Re-assign row elements
        for r in self._rows:
            r.web_element = new_row_web_elements[r.row_index]      

    def calculate_all_row_clickable_web_elements(self):
        # Calculate rows if necessary
        if self._rows == []:
            self.recalculate_rows()
      
        # Rows for which web_element is already clickable
        if self.row_clickable_query == None:
            if self._rows[0]._web_element == None:  #TODO: stick to public attrs
                self.calculate_all_row_web_elements()
            else:
                for r in self._rows:
                    r.clickable_web_element = r.web_element
        
        else:
            # Calculate all clickable row elements
            wait = WebDriverWait(self.web_element, TIMEOUT)
            new_row_clickable_web_elements = wait.until(EC.presence_of_all_elements_located(self.row_clickable_query))

            # Re-assign clickable row elements
            for r in self._rows:        #TODO: self._rows or self.rows???
                r.clickable_web_element = new_row_clickable_web_elements[r.row_index]   #TODO: check indexing

    @property
    def web_element(self):
        """
        Web element for the table in the DOM. Recalculated if necessary.
        """
        if self._web_element == None:
            self._web_element = self.get_web_element(self.driver)
        return self._web_element
    
    def get_web_element(self, driver, fail_cap: int = -1):
        """
        Find the web element for the table. By default, the driver will keep 
        polling the DOM indefinitely until it finds the table. Set a `fail_cap`
        to a positive value to limit the number of times the DOM can be polled.
        """
        wait = WebDriverWait(driver, TIMEOUT)
        fail_count = 0
        while fail_count < fail_cap or fail_cap < 0:
            try:
                table_elements = wait.until(EC.presence_of_all_elements_located(self.table_query))
            except TimeoutException:
                print(f'Warning: table not found. Trying again... ({fail_count = })')
                fail_count += 1
                continue
            else:
                return table_elements[self.table_index]
    
    def recalculate_web_element(self):
        self._web_element = None
        self._web_element = self.web_element    # better way to use setter?

class Row:
    """A Row is clickable."""
    def __init__(self, parent_table: Table, row_index: int, query: tuple):
        # Set initial instance attributes
        self.parent_table = parent_table
        self.row_index = row_index
        self.query = query

        # Set private/container instance attributes
        self._web_element = None
        self._clickable_web_element = None
        self._name = None

    @property
    def web_element(self):
        if self._web_element == None:
            self._web_element = self.get_web_element()
        return self._web_element
    
    @web_element.setter
    def web_element(self, e):
        self._web_element = e
        self.recalculate_name()

    def get_web_element(self, fail_cap: int = -1, recalculate_table_element: bool = False):
        fail_count = 0
        while fail_count < fail_cap or fail_cap < 0:
            try:
                wait = WebDriverWait(self.parent_table.web_element, TIMEOUT)
                elements = wait.until(EC.presence_of_all_elements_located(self.query))
            except (TimeoutException, NoSuchElementException) as e:
                print(f'Warning: {type(e)} was encountered - row could not be found. Trying again... ({fail_count = })')
                if recalculate_table_element:
                    self.parent_table.recalculate_web_element()
            else:
                return elements[self.row_index]
    
    @property
    def clickable_web_element(self):
        # Recalculate clickable element if necessary
        if self._clickable_web_element == None:
            # Row queries defined in Table.rows correspond to the following:
            # object rows are already clickable
            if self.parent_table.table_type == 'object':
                self._clickable_web_element = self.web_element
            
            # link rows must be further searched to find the clickable links
            elif self.parent_table.table_type == 'link':
                wait = WebDriverWait(self.web_element, TIMEOUT)
                self._clickable_web_element = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, ".//td[@class='Data l']/a")
                    )
                )
        
        return self._clickable_web_element
    
    @clickable_web_element.setter
    def clickable_web_element(self, e):
        self._clickable_web_element = e
    
    def recalculate_clickable_web_element(self):
        self._clickable_web_element = None
        self._clickable_web_element = self.clickable_web_element
    
    def click(self):
        self.clickable_web_element.click()
    
    @property
    def name(self):
        if self._name == None:
            self._name = self.web_element.text.rsplit(' ', 1)[0]
        return self._name
    
    def recalculate_name(self):
        self._name = None
        self._name = self.name

class AxisMenu:
    """An AxisMenu is a clickable collection of Options."""
    def __init__(self, driver, webpage_type, axis_index):
        # Set instance attributes
        self.driver = driver
        self.webpage_type = webpage_type

        # Calculate menus
        wait = WebDriverWait(driver, TIMEOUT)
        #TODO: account for object-broken and link-broken
        if 'object' in webpage_type:
            menus = wait.until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//button[starts-with(@id, 'headlessui-listbox-button')]")
                )
            )
        elif 'link' in webpage_type:
            menus = wait.until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//select[starts-with(@id, 'dimension_pick')]")
                )
            )
        self.clickable_element = menus[axis_index]

        # Calculate options
        # Note: Chrome and Edge can encounter stale element references when 
        #       the webpage is of type 'object-whole', so the calculation is 
        #       wrapped in a while-try-except-else block
        while True:
            try:
                self.calculate_options()
            except StaleElementReferenceException:
                sleep(0.01)
            else:
                break

    def calculate_options(self):
        if 'object' in self.webpage_type:
            # Listbox is not contained in the clickable element, and options
            # are inside it. The clickable element must be clicked before
            # the listbox will appear.
            self.click()
            wait = WebDriverWait(self.driver, TIMEOUT)
            listbox_element = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//ul[starts-with(@id, 'headlessui-listbox-options')]")
            ))

            wait = WebDriverWait(listbox_element, TIMEOUT)
            option_elements = wait.until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, ".//*[@role='option']/li/span")
                )
            )

        elif 'link' in self.webpage_type:
            # options are inside the clickable element
            wait = WebDriverWait(self.clickable_element, TIMEOUT)
            option_elements = wait.until(EC.presence_of_all_elements_located(
                    (By.XPATH, f".//option")
            ))
        self.options = [Option(e) for e in option_elements]

    def click(self):
        self.clickable_element.click()

    def set_to(self, axis_name: str):
        # For object-based, have to re-calculate options because the references
        # calculated previously have turned stale
        # Note: Chrome and Edge can encounter stale element references when 
        #       the webpage is of type 'object-whole', so the calculation is 
        #       wrapped in a while-try-except-else block
        if 'object' in self.webpage_type:
            while True:
                try:
                    self.calculate_options()   # note: this automatically clicks
                except StaleElementReferenceException:
                    sleep(0.01)
                else:
                    break
        elif 'link' in self.webpage_type:
            self.click()                    # opens the menu

        # Select the given option
        # TODO: is there a better way to do this than list comprehension?
        option_to_click = [o for o in self.options if o.name == axis_name]
        option_to_click[0].click()

    def calculate_all(driver, webpage_type):
        if webpage_type == 'object-whole':
            menus = [AxisMenu(driver, webpage_type, i) for i in range(3)]
        elif webpage_type == 'link-whole':
            menus = [AxisMenu(driver, webpage_type, i) for i in range(3)]
        elif webpage_type == 'object-broken':
            pass        #TODO: add this
        elif webpage_type == 'link-broken':
            pass        #TODO: add this
        return menus
    
    @property
    def option_names(self):
        return [o.name for o in self.options]

class Option:
    """An Option is clickable and has a name."""
    def __init__(self, clickable_web_element):
        self.clickable_element = clickable_web_element
        self.name = clickable_web_element.text  #StaleElementReferenceException can get thrown here
    
    def click(self):
        self.clickable_element.click()


class CollationEngine():
    # For first implementation, user will specify three axes which will correspond
    # to the axes selected in the browser for the three tables (left to right).
    # In future versions, I want the user to be able to specify an arbitrary number
    # of axes, and have the engine construct a dataset that includes all of them.
    def __init__(self, browser: SUPPORTED_BROWSERS, url: str, 
                 filename: str | Path, axes: list[str], headless: bool=False):
        # Validate Input
        self.validate_input(browser, url, filename, axes, headless)
        
        # Set instance attributes
        self.browser = browser
        self.driver = self.get_driver(browser, headless)
        self.filename = filename
        self.axes = axes
        self.tables = [None, None, None]

        # Determine webpage type
        self.webpage_type = WEBPAGE_TYPES[url]

        # Go to webpage
        self.driver.get(url)

        # Calculate Menus
        # TODO: this currently doesn't work for broken-out webpages
        self.menus = AxisMenu.calculate_all(self.driver, self.webpage_type)

        # Calculate tables
        # TODO: this currently doesn't work for broken-out webpages
        if self.webpage_type in ('object-whole', 'object-broken'):
            table_type = 'object'
        elif self.webpage_type in ('link-whole', 'link-broken'):
            table_type = 'link'
        self.tables = [Table(self.driver, i, table_type) for i in range(3)]

        # Check for valid input axis names
        # Note: technically, all menus should have the same options, but this
        #       will not always be the case if support is added for more webpage
        #       types, so all menus will be checked
        for m in self.menus:
            for a in self.axes:
                if a not in m.option_names:
                    raise ValueError(f"Axis name {a} could not be found")

        # Set Axes
        for i, a in enumerate(self.axes):
            self.menus[i].set_to(a)

        # Dataset
        self.create_dataset()
        self.clean_dataset()
        self.save_dataset()
    
        # close browser
        sleep(10)
        self.driver.close()

    def validate_input(self, browser: SUPPORTED_BROWSERS, url: str, 
                       filename: str | Path, axes: list[str], headless: bool):
        """Check that input parameters are valid."""
        # Check for valid browser
        if browser not in get_args(SUPPORTED_BROWSERS):
            msg = "browser must be one of the following: "
            msg += ', '.join(get_args(SUPPORTED_BROWSERS))
            raise TypeError(msg)
        
        # Check for valid filename type
        if type(filename) not in (str, type(Path())):
            raise TypeError(f"filename must be of type str or Path")

        # Make path of output file absolute
        filename = Path(filename)
        if not filename.is_absolute():
            filename = filename.resolve()

        # Check that we have permission to write the output file
        testfilename = filename.parent / 'test.txt'
        try:
            testfile = open(testfilename, 'w')
        except (OSError, IOError):
            msg = f"Error: Cannot write a file to the folder {filename.parent}."
            msg += "\nPlease enter a different value for `filename`."
            print(msg)
            quit()
        else:
            testfile.close()
            try:
                os.remove(testfilename)
            except OSError:
                msg = f"Warning: temporary file could not be deleted: {testfilename}"
                msg += "\nPlease delete file manually after execution is complete."
                print(msg)
        
        # Check for valid URL
        if WEBPAGE_TYPES[url] not in FULLY_SUPPORTED_TYPES:
            if WEBPAGE_TYPES[url] in PARTIALLY_SUPPORTED_TYPES:
                print("Warning: URL is not fully supported. Retrieving anyway...")
            elif url in WEBPAGE_TYPES.keys():
                raise ValueError("URL is not supported")
            else:
                raise ValueError("URL is not recognized")
            
        # Check for valid headless flag
        if type(headless) != bool:
            raise TypeError("headless must be of type bool")
        

    def get_driver(self, browser: SUPPORTED_BROWSERS, headless):
        """Import necessary classes and return webdriver for the chosen browser."""
        if browser == 'Firefox':
            from selenium.webdriver import Firefox                  
            from selenium.webdriver.firefox.options import Options
            options = Options()
            if headless:
                options.add_argument('--headless')
            return Firefox(options=options)
        
        elif browser == 'Chrome':
            from selenium.webdriver import Chrome
            from selenium.webdriver.chrome.options import Options
            options = Options()
            if headless:
                options.add_argument('--headless')
            return Chrome(options=options)
        
        elif browser == 'Edge':
            from selenium.webdriver import Edge
            from selenium.webdriver.edge.options import Options
            options = Options()
            if headless:
                options.add_argument('--headless')
            return Edge(options=options)

        elif browser == 'Safari':
            from selenium.webdriver import Safari
            from selenium.webdriver.safari.options import Options
            options = Options()
            if headless:
                options.add_argument('--headless')
            return Safari(options=options)

    def create_dataset(self,
                       data: Optional[dict | None] = None, 
                       current_t1_row: Optional[int | None] = None, 
                       current_t2_row: Optional[int | None] = None):
        """
        Create a dataset of nested dictionaries from the webpage.
        
        If called with its optional parameters, this method will initialize the 
        dataset with the provided dictionary `data`, and only get data from rows
        including and after `current_t1_row` (for Table 1) and `current_t2_row`
        for (Table 2).

        Raises DatasetException if a stale element reference is found.
        """
        # Set progress bar formatting
        pbar_format = "{desc}{percentage:3.0f}%|{bar:30}| {n_fmt}/{total_fmt} [{rate_fmt}{postfix}]"
        
        # Initialize data container dictionary
        data = {}

        # Iterate over table 1 rows
        pbar1 = tqdm(self.tables[0].rows, leave=False, bar_format=pbar_format)
        for i, t1_row in enumerate(pbar1):  #https://stackoverflow.com/a/45519268/15426433
            pbar1.set_description(shorten(f"Table 1: {t1_row.name}"))

            data[t1_row.name] = {}

            t1_row.click()

            # Re-calculate rows for table 2
            # sleep needed to make sure recalculation happens properly on Chrome and Edge
            if self.browser in ['Chrome', 'Edge']:
                sleep(0.1)
            self.tables[1].recalculate_text_rows()
            self.tables[1].recalculate_rows()
            
            # Iterate over table 2 rows
            pbar2 = tqdm(self.tables[1].rows, leave=False, bar_format=pbar_format)
            for j, t2_row in enumerate(pbar2):
                pbar2.set_description(shorten(f"Table 2: {t2_row.name}"))  
            
                t2_row.click()

                # Re-calculate rows for table 3
                # sleep needed to make sure recalculation happens properly on Chrome and Edge
                if self.browser in ['Chrome', 'Edge']:
                    sleep(0.1)
                self.tables[2].recalculate_text_rows()
                self.tables[2].recalculate_rows()

                # Copy rows from table 3 into the data dictionary
                t3_rows = self.tables[2].text_rows
                t3_rows = [r.rsplit(' ', 1) for r in t3_rows]
                t3_rows = [[r[0], int(r[1].replace(',', ''))] for r in t3_rows]
                data[t1_row.name][t2_row.name] = {r[0]: r[1] for r in t3_rows}
        
        # Save data as attribute and convert to dataframe
        self.data = data
        self.df = pd.concat(                # https://stackoverflow.com/a/54300940
            {k: pd.DataFrame(v).T for k, v in data.items()}, 
            axis=0
        )

    def clean_dataset(self):
        # Rectify missing second-level index entries
        unique_index1 = self.df.index.unique(0)
        unique_index2 = self.df.index.unique(1)
        new_index = pd.MultiIndex.from_product([unique_index1, unique_index2])
        self.df = self.df.reindex(new_index, axis='index')

        # Change all NaN values to 0
        self.df = self.df.fillna(value=0.0)

        # Sort df rows
        self.df = self.df.sort_index()

        # Sort df columns
        self.df = self.df.reindex(sorted(self.df.columns), axis=1)

        # Add a Total Column
        self.df['Total'] = self.df.sum(axis=1)

        # Convert all floats to int (cannot have fractions of people)
        float_cols = self.df.select_dtypes(include=['float64'])
        for col in float_cols.columns.values:
            self.df[col] = self.df[col].astype('int64')

        # Rename indices to reflect axis names
        for i, a in enumerate(self.axes[:-1]):
            self.df.index.rename(names=a, level=i, inplace=True)     
            
    def save_dataset(self):
        self.df.to_hdf(self.filename, key='TRACDataset')

def shorten(text, 
            text_limit=24, 
            terminator='...', 
            delimiter='',
            padding=' ',
            pad_limit=25):
    """Shorten a string to the specified limit, adding additional padding."""
    if len(text) > text_limit:
        text = text[:text_limit - 1 - len(terminator)] + terminator + delimiter
    
    text += delimiter + (padding * (pad_limit - len(text)))
    return text


if __name__ == '__main__':
    engine = CollationEngine(
        browser='Chrome',
        url='https://trac.syr.edu/phptools/immigration/cbparrest/',
        filename='cbparrestschrome.hdf',
        axes=['Gender', 'Special Initiatives', 'Marital Status'],
        headless=False
    )