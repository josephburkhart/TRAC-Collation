"""
This module contains classes that can collate multi-axis data from one of 
a set number of TRAC webpages.

This module can be run as a  as a standalone script. To set the parameters for
the standalone script, see STANDALONE_PARAMS below.
"""

## Browser-agnostic imports
# Note: Browser-specific imports are handled in CollateEngine.get_driver()
import warnings
warnings.filterwarnings("ignore")       # ignore warnings from pandas

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
import sys

## Constants
STANDALONE_PARAMS = {
    "browser": 'Chrome',
    "url": 'https://tracreports.org/phptools/immigration/cbparrest/',
    "filename": 'cbparrestschrome.hdf',
    "axes": ['Gender', 'Special Initiatives', 'Marital Status'],
    "headless": True,
    "optimize": False
}

USAGE = (
    f"Collate data from a TRAC webpage.\n\n"
    f"If called without arguments, the program will prompt the user for "
    f"each \nargument. If called with neither options nor arguments, the " 
    f"program will \nrun with standalone/demo parameters.\n\n"
    f"Usage: python {sys.argv[0]} (options) [(<url> <file> <axes>)]\n\n"
    f"Options:\n"
    f"\t--browser=<n>\tName of the browser to use. Valid names are \n"
    f"\t\t\t'Firefox', 'Chrome', 'Edge', and 'Safari'.\n"
    f"\t[--headless]\tUse the browser in headless mode.\n"
    f"\t[--optimize]\tOptimize data traversal for fewest clicks and waits.\n"
    f"\t[-h, --help]\tShow this screen.\n\n"
    f"Arguments:\n"
    f"\turl\tFull address of the TRAC webpage.\n"
    f"\tfile\tName or full path of the output file.\n"
    f"\taxes\tComma-separated list of the names of the axes of interest.\n"
    f"\t\tNote that the list must be enclosed in \"\" if any names \n"
    f"\t\tinclude spaces." 
)

WEBPAGE_TYPES = {
    'https://tracreports.org/phptools/immigration/ntanew/': 'object-broken',
    'https://tracreports.org/phptools/immigration/closure/': 'object-broken',
    'https://tracreports.org/phptools/immigration/asyfile/': 'object-whole',
    'https://tracreports.org/phptools/immigration/asylum/': 'object-whole',
    'https://tracreports.org/phptools/immigration/mpp4/': 'link-whole',
    'https://tracreports.org/phptools/immigration/juvenile/': 'link-whole',
    'https://tracreports.org/phptools/immigration/mwc/': 'link-whole',
    'https://tracreports.org/phptools/immigration/cbparrest/': 'link-whole',
    'https://tracreports.org/phptools/immigration/cbpinadmiss/': 'object-whole',
    'https://tracreports.org/phptools/immigration/arrest/': 'link-whole',
    # 'https://tracreports.org/phptools/immigration/detainhistory/': 'link-whole',
    'https://tracreports.org/phptools/immigration/remove/': 'link-whole',
    'https://tracreports.org/phptools/immigration/removehistory/': 'link-whole',
    'https://tracreports.org/phptools/immigration/secure/': 'link-whole',
    'https://tracreports.org/phptools/immigration/backlog/': 'object-broken',
    'https://tracreports.org/phptools/immigration/addressrep/': 'map-table',
    'https://tracreports.org/immigration/reports/judgereports/': 'table-only-1',
    'https://tracreports.org/phptools/immigration/asylumbl/': 'object-broken',
    'https://tracreports.org/phptools/immigration/bond/': 'table-tab',
    'https://tracreports.org/phptools/immigration/detention/': 'link-broken',
    'https://tracreports.org/immigration/detentionstats/facilities.html': 'table-only-2',
    'https://tracreports.org/immigration/detentionstats/atd_pop_table.html': 'table-only-2'
}

FULLY_SUPPORTED_TYPES = ['object-whole', 'link-whole']
PARTIALLY_SUPPORTED_TYPES = ['object-broken', 'link-broken']

TIMEOUT = 10

SUPPORTED_BROWSERS = Literal['Chrome', 'Edge']
# SUPPORTED_BROWSERS = Literal['Firefox', 'Chrome', 'Edge', 'Safari']

WAIT_TIME_FOR_POPULATION = 0.2

STALE_REFERENCE_MAX_ATTEMPTS = 1000

## Classes
class Table:
    """
    A Table is a collection of Rows.
    
    Args:
        driver: The webdriver object that is accessing the webpage.
        table_index: An integer indicating which table on the webpage this Table 
                     is for (0 = left, 1 = middle, 2 = right).
        table_type: A string representing the kind of table element this Table 
                    is for. This string is used to determine how to poll the DOM
                    for table rows and other important elements.
        wait_time: A float indicating how long to wait for elements to populate.
    """
    def __init__(self, 
                 driver, 
                 table_index: int, 
                 table_type: Literal['object', 'link'],
                 wait_time: float):
        # Set initial instance attributes
        self.driver = driver
        self.table_index = table_index
        self.table_type = table_type
        self.wait_time = wait_time

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
        List of strings representing the useful rows from this Table, without
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
    
    @property
    def rows(self):
        """
        List of Row objects for this Table, of the same length as text_rows.
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
            
        return self._rows
    
    def recalculate_rows(self, also_web_elements=False, also_clickable_web_elements=False):
        """Erase and re-generate all internal data about rows.
        
        By default, does not recalculate web elements or clickable web elements.
        """
        self._text_rows = []
        self._text_rows = self.text_rows

        self._rows = []
        self._rows = self.rows  # better way to use setter?

        if also_web_elements:
            self.calculate_all_row_web_elements()
        
        if also_clickable_web_elements:
            self.calculate_all_row_clickable_web_elements()


    def calculate_all_row_web_elements(self, also_rows=False):
        """
        Calculate web elements for all Row objects in this Table, and assign 
        each one to its respective Row.
        
        This method is faster than calling Row.get_web_element() on each Row
        object because it polls the DOM for all of the elements at once.

        Returns: None
        """
        # Calculate rows if necessary
        if self._rows == [] or also_rows:
            self.recalculate_rows()
      
        # Calculate all row elements
        try:
            wait = WebDriverWait(self.web_element, TIMEOUT)
            new_row_web_elements = wait.until(EC.presence_of_all_elements_located(self.row_query))
        except StaleElementReferenceException:
            self.recalculate_web_element()
            wait = WebDriverWait(self.web_element, TIMEOUT)
            new_row_web_elements = wait.until(EC.presence_of_all_elements_located(self.row_query))

        # Re-assign row elements
        # TODO: figure out why IndexError is sometimes thrown
        try:
            for r in self._rows:
                r.web_element = new_row_web_elements[r.row_index]
        except IndexError:
            self.recalculate_rows()
            for r in self._rows:
                r.web_element = new_row_web_elements[r.row_index]

    def calculate_all_row_clickable_web_elements(self, also_rows=False):
        """
        Calculate clickable web elements for all Row objects in this Table, and
        assign each one to its respective Row.

        This method is faster than calling Row.get_web_element() on each Row
        object because it polls the DOM for all of the clickable elements at 
        once.
        """
        # Calculate rows if necessary
        if self._rows == [] or also_rows:
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
            # Table.calculate_all_row_web_elements() can encounter an IndexError
            # so I should prepare for encountering one here as well
            try:
                for r in self._rows:
                    r.clickable_web_element = new_row_clickable_web_elements[r.row_index]   #TODO: check indexing
            except IndexError:
                self.recalculate_rows()
                for r in self._rows:
                    r.clickable_web_element = new_row_clickable_web_elements[r.row_index]

    @property
    def web_element(self):
        """
        Web element for this Table, automatically calculated if necessary.
        """
        if self._web_element == None:
            self._web_element = self.get_web_element(self.driver)
        return self._web_element
    
    def get_web_element(self, driver, attempt_cap: int = -1):
        """
        Find the web element for this Table. By default, the driver will keep 
        polling the DOM indefinitely until it finds the table. Set `attempt_cap`
        to a positive value to limit the number of times the DOM can be polled.
        """
        wait = WebDriverWait(driver, TIMEOUT)
        attempt_count = 0
        while attempt_count < attempt_cap or attempt_cap < 0:
            try:
                table_elements = wait.until(EC.presence_of_all_elements_located(self.table_query))
            except TimeoutException as e:
                print(f'Warning: {type(e)} encountered - table not found. Trying again... ({attempt_count = })')
                attempt_count += 1
            else:
                return table_elements[self.table_index]
    
    def recalculate_web_element(self):
        self._web_element = None
        self._web_element = self.web_element    # better way to use setter?

class Row:
    """
    A Row is clickable and has a name and a value.
    
    Args:
        parent_table: The Table object that contains this Row.
        row_index: A string indicating which row in `parent_table` this Row
                   corresponds to. Index order is ascending from top to bottom.
        query: A tuple representing the query to use when polling the DOM for
               this row's web element. Example: `(By.CLASS_NAME, 'table-fixed')`
    """
    def __init__(self, parent_table: Table, row_index: int, query: tuple):
        # Set initial instance attributes
        self.parent_table = parent_table
        self.row_index = row_index
        self.query = query

        # Set private/container instance attributes
        self._web_element = None
        self._clickable_web_element = None
        self._name = None
        self._value = None

    @property
    def web_element(self):
        """Web element for this Table, automatically calculated if necessary."""
        if self._web_element == None:
            self._web_element = self.recalculate_web_element()
        return self._web_element
    
    @web_element.setter
    def web_element(self, e):
        """Whenenver the web element is explicitly set, recalculate the name and value."""
        self._web_element = e
        self.recalculate_name_and_value()

    def recalculate_web_element(self, attempt_cap: int = -1, recalculate_table_element: bool = False):
        """Find the web element for this Row. By default, the driver will keep
        polling the DOM indefinitely until it finds the row. Set `fail_cap` to
        a positive value to limit the number of times the DOM can be polled.
        
        Optionally, a flag can be set to recalculate the web element for the
        parent if the row cannot be found (defaults to False)."""
        attempt_count = 0
        while attempt_count < attempt_cap or attempt_cap < 0:
            try:
                wait = WebDriverWait(self.parent_table.web_element, TIMEOUT)
                elements = wait.until(EC.presence_of_all_elements_located(self.query))
            except (TimeoutException, NoSuchElementException) as e:
                print(f'Warning: {type(e)} was encountered - row could not be found. Trying again... ({attempt_count = })')
                attempt_count += 1
                if recalculate_table_element:
                    self.parent_table.recalculate_web_element()
            else:
                try:    # TODO: this is ugly
                    return elements[self.row_index]
                except IndexError:
                    raise IndexError(f"{self.row_index=}, {len(elements)=}, {elements=}")

    @property
    def clickable_web_element(self):
        """
        Web element for this Row that can be clicked to filter other Tables.
        """
        # Recalculate clickable element if necessary
        if self._clickable_web_element == None:
            # Row queries defined in Table.rows correspond to the following:
            # object rows are already clickable
            # TODO: to re-factor for consistency, create get_clickable_web_element()
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
        attempt_count = 0
        while attempt_count < STALE_REFERENCE_MAX_ATTEMPTS:
            try:
                self.clickable_web_element.click()
                break
            except StaleElementReferenceException as e:
                print(f"Warning: {e} encountered - row could not be found. Trying again... ({attempt_count = })")
                attempt_count += 1

                self.parent_table.calculate_all_row_web_elements()
                self.parent_table.calculate_all_row_clickable_web_elements()
                # self.recalculate_web_element()
                # self.recalculate_clickable_web_element()
                sleep(self.parent_table.wait_time)

    
    @property
    def name(self):
        """Name of this Row, corresponding to the text in the left column."""
        if self._name == None:
            attempt_count = 0
            while attempt_count < STALE_REFERENCE_MAX_ATTEMPTS:
                try:
                    self._name = self.web_element.text.rsplit(' ', 1)[0]
                    break
                except StaleElementReferenceException as e:
                    print(f"Warning: {e} encountered - row could not be found. Trying again... ({attempt_count = })")
                    attempt_count += 1

                    self.parent_table.calculate_all_row_web_elements()  # previously self.recalculate_web_element()
                    sleep(self.parent_table.wait_time)
        
        return self._name
    
    @property
    def value(self):
        """Value of this Row, corresponding to the text in the right column."""
        if self._value == None:
            attempt_count = 0
            while attempt_count < STALE_REFERENCE_MAX_ATTEMPTS:
                try:
                    self._value = int(self.web_element.text.rsplit(' ', 1)[1].replace(",", ""))
                except StaleElementReferenceException as e:
                    print(f"Warning: {e} encountered - row could not be found. Trying again... ({attempt_count = })")
                    attempt_count += 1

                    self.parent_table.calculate_all_row_web_elements()  # previously self.recalculate_web_element()
                    sleep(self.parent_table.wait_time)
                else:
                    break

        return self._value
    
    def recalculate_name_and_value(self):
        self._name = None
        self._name = self.name

        self._value = None
        self._value = self.value

class AxisMenu:
    """
    An AxisMenu is a clickable collection of Options.
    
    Args:
        driver: The webdriver object that is accessing the webpage.
        webpage_type: A string representing the type of the webpage.
        axis_index: An integer indicating which menu on the webpage this 
                    AxisMenu is for (0 = left, 1 = middle, 2 = right).
        wait_time: A float indicating how long to wait for elements to populate.
    """
    def __init__(self, driver, webpage_type: str, axis_index: int, wait_time):
        # Set instance attributes
        self.driver = driver
        self.webpage_type = webpage_type
        self.wait_time = wait_time

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
                sleep(wait_time)
            else:
                break

    def calculate_options(self):
        """
        Find all of the options in this AxisMenu and store them in self.options.
        """
        if 'object' in self.webpage_type:
            # Listbox is not contained in the clickable element, and options
            # are inside it. The clickable element must be clicked before
            # the listbox will appear.
            # TODO: possible bug on object webpages that causes is an extra
            #       empty option
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
        """Set the axis for this AxisMenu to one of its Options."""
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
                    sleep(self.wait_time)
                else:
                    break
        elif 'link' in self.webpage_type:
            self.click()                    # opens the menu

        # Select the given option
        # TODO: is there a better way to do this than list comprehension?
        option_to_click = [o for o in self.options if o.name == axis_name]
        try:
            option_to_click[0].click()
        except StaleElementReferenceException:
            self.calculate_options()
            option_to_click = [o for o in self.options if o.name == axis_name]
            option_to_click[0].click()

    def calculate_all(driver, webpage_type, wait):
        """Calculate all AxisMenus for this webpage."""
        if webpage_type == 'object-whole':
            menus = [AxisMenu(driver, webpage_type, i, wait) for i in range(3)]
        elif webpage_type == 'link-whole':
            menus = [AxisMenu(driver, webpage_type, i, wait) for i in range(3)]
        elif webpage_type == 'object-broken':
            menus = [AxisMenu(driver, webpage_type, i, wait) for i in range(3)]        #TODO: add proper support for this
        elif webpage_type == 'link-broken':
            menus = [AxisMenu(driver, webpage_type, i, wait) for i in range(3)]        #TODO: add proper support for this
        return menus
    
    @property
    def option_names(self):
        """List of the name of each Option object for this AxisMenu."""
        return [o.name for o in self.options]

class Option:
    """
    An Option is clickable and has a name.
    
    Args:
        clickable_web_element: The clickable web element for this Option.
    """
    def __init__(self, clickable_web_element):
        self.clickable_element = clickable_web_element
        self.name = clickable_web_element.text  #TODO: StaleElementReferenceException can get thrown here
    
    def click(self):
        self.clickable_element.click()


class CollationEngine():
    """
    A CollationEngine coordinates the other classes in collating the webpage.

    Args:
        browser: A string representing the name of the web browser to use for 
                 accessing the webpage at `url`. Must be one of the following: 
                 'Firefox', 'Chrome', 'Edge', or 'Safari'.
        url: A string representing the URL of the webpage to collate data from.
             For a list of supported webpages, see `WEBPAGE_TYPES` and
             `FULLY_SUPPORTED_WEBPAGE_TYPES`.
        filename: A string or Path object representing the name or path of the
                  output data file. This input is validated to make sure that
                  write permissions are held for this location.
        axes: A list of strings representing the names of the axes to use when
              collating data from the webpage.
        headless: A boolean representing whether or not to driver the browser in
                  headless mode. In headless mode, the browser does not have a
                  visible window, so no graphical rendering is performed and no
                  manual interaction with the browser instance is possible.
                  Defaults to False.
        optimize: A boolean that specifies whether to optimize data traversal
                  by ordering the axes from fewest possible values to most 
                  possible values, thereby minimizing the number of clicks and
                  waits. Defaults to False.
        hdf_key: An optional string that will be used as a key when saving the
                 dataset to HDF. Users who wish to save multiple datasets to
                 the same HDF file will need to specify a unique key each time.
                 Defaults to 'TRACDataset'.
        run_immediately: A boolean that specifies whether to immediately create 
                         the dataset, clean it, and save it, and then close the
                         browser. Defaults to True.
    """
    def __init__(self, 
                 browser: SUPPORTED_BROWSERS, 
                 url: str, 
                 filename: str | Path, 
                 axes: list[str], 
                 headless: bool=False,
                 optimize: bool=False,
                 hdf_key: str="TRACDataset",
                 run_immediately: bool=True):
        print("Initializing collation engine... ", end="")

        # Validate Input
        self.validate_input(browser, url, filename, axes, headless, optimize)
        
        # Set instance attributes
        self.browser = browser
        self.driver = CollationEngine.get_driver(browser, headless)
        self.filename = filename
        self.axes = axes
        self.tables = [None, None, None]
        self.optimize = optimize
        self.hdf_key = hdf_key
        self.axes_order = list(range(len(axes)))

        # If using Chrome, prevent the graph from loading, since it tremendously
        # slows down the webpage. 
        # TODO: I want to do this for Firefox but I can't figure out how.
        if self.browser in ["Chrome", "Edge"]:
            self.driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": [f"{url}graph.php"]})
            self.driver.execute_cdp_cmd("Network.enable", {})

        self.wait_time = WAIT_TIME_FOR_POPULATION

        # Determine webpage type
        self.webpage_type = WEBPAGE_TYPES[url]

        # Go to webpage
        self.driver.get(url)

        # Calculate Menus
        # TODO: this currently doesn't work for broken-out webpages
        self.menus = AxisMenu.calculate_all(self.driver, 
                                            self.webpage_type,
                                            self.wait_time)

        # Calculate tables
        # TODO: this currently doesn't work for broken-out webpages
        if self.webpage_type in ('object-whole', 'object-broken'):
            table_type = 'object'
        elif self.webpage_type in ('link-whole', 'link-broken'):
            table_type = 'link'
        self.tables = [Table(self.driver, i, table_type, self.wait_time) for i in range(3)]

        # Check for valid input axis names
        # Note: technically, all menus should have the same options, but this
        #       will not always be the case if support is added for more webpage
        #       types, so all menus will be checked
        for m in self.menus:
            for a in self.axes:
                if a not in m.option_names:
                    raise ValueError(f"Axis name '{a}' could not be found")

        # Set Axes
        if self.optimize:
            print("Optimizing... ", end="")
            n_values = []
            for a in self.axes:
                self.menus[0].set_to(a)
                sleep(self.wait_time)
                table = Table(self.driver, 0, table_type, self.wait_time)
                n_values.append(len(table.text_rows))

            self.axes_order = [
                i[0] for i in sorted(enumerate(n_values), key=lambda x: x[1])
            ]
            print(f"Reordering axes to {self.axes_order} for better performance... ", end="")

        for i, o in enumerate(self.axes_order):
            self.menus[i].set_to(self.axes[o])

        print("Done.")

        # Run if necessary
        if run_immediately:
            self.run()

    def validate_input(self, 
                       browser: SUPPORTED_BROWSERS, 
                       url: str, 
                       filename: str | Path, 
                       axes: list[str], 
                       headless: bool,
                       optimize: bool):
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
            msg = (f"Cannot write a file to the folder {filename.parent}. "
                   f"Please enter a different value for filename.")
            raise RuntimeError(msg)
        else:
            testfile.close()
            try:
                os.remove(testfilename)
            except OSError:
                msg = (f"Warning: temporary file could not be deleted: {testfilename} "
                       f"Please delete file manually after execution is complete.")
                warnings.warn(msg)
        
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
        
        # Check for valid optimize flag
        if type(optimize) != bool:
            raise TypeError("optimize must be of type bool")

    @staticmethod
    def get_driver(browser: SUPPORTED_BROWSERS, headless):
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

    def create_dataset(self):
        """
        Create a dataset of nested dictionaries from the webpage.
        """
        # Set progress bar formatting
        pbar_format = "{desc}{percentage:3.0f}%|{bar:30}| {n_fmt}/{total_fmt} [{rate_fmt}{postfix}]"
        
        # Initialize data container dictionary
        data = {}

        # Iterate over table 1 rows
        self.tables[0].recalculate_rows()
        sleep(self.wait_time)

        t1_total_expected = sum([r.value for r in self.tables[0].rows])
        t1_total_actual = 0

        while t1_total_expected != t1_total_actual:
            t1_total_actual = 0

            pbar1 = tqdm(
                range(len(self.tables[0].text_rows)), 
                leave=False, 
                bar_format=pbar_format
            )
            for i in pbar1:
                # self.tables[0].recalculate_rows()
                t1_row = self.tables[0].rows[i]
                pbar1.set_description(shorten(f"Table 1: {t1_row.name}"))

                data[t1_row.name] = {}

                t1_row.click()
                sleep(self.wait_time)
                self.tables[1].recalculate_rows()
                
                while t1_row.value != sum([r.value for r in self.tables[1].rows]):
                    sleep(self.wait_time)
                    self.tables[1].recalculate_rows()
                    
                # Iterate over table 2 rows
                t2_total_expected = t1_row.value
                t2_total_actual = 0

                while t2_total_expected != t2_total_actual:
                    t2_total_actual = 0

                    pbar2 = tqdm(
                        range(len(self.tables[1].text_rows)), 
                        leave=False, 
                        bar_format=pbar_format
                    )
                    for j in pbar2:
                        # self.tables[1].recalculate_rows()
                        t2_row = self.tables[1].rows[j]
                        pbar2.set_description(shorten(f"Table 2: {t2_row.name}")) 

                        t2_row.click()

                        sleep(self.wait_time)
                        self.tables[2].recalculate_rows()

                        while t2_row.value != sum([r.value for r in self.tables[2].rows]):
                            sleep(self.wait_time)
                            self.tables[2].recalculate_rows()

                        # Copy rows from table 3 into the data dictionary
                        t3_rows = self.tables[2].text_rows
                        t3_rows = [r.rsplit(' ', 1) for r in t3_rows]
                        t3_rows = [[r[0], int(r[1].replace(',', ''))] for r in t3_rows]
                        data[t1_row.name][t2_row.name] = {r[0]: r[1] for r in t3_rows}

                        # Keep t2 tally for sanity check
                        t2_total_actual += sum(data[t1_row.name][t2_row.name].values())
                
                t1_total_actual += t2_total_actual
        
        # Save data as attribute and convert to dataframe
        self.data = data
        self.df = pd.concat(                # https://stackoverflow.com/a/54300940
            {k: pd.DataFrame(v).T for k, v in data.items()}, 
            axis=0
        )

    def clean_dataset(self):
        """Clean the raw collated dataset to ensure clarity and completeness."""
        # Ensure index and column order match what the user specified
        if self.optimize and self.axes_order != sorted(self.axes_order):
            self.df = self.df.stack()
            col_order_index = self.axes_order.index(max(self.axes_order))

            self.df = self.df.unstack(col_order_index)

            idx_order = [i for i in self.axes_order if i!=max(self.axes_order)]
            self.df = self.df.reorder_levels(idx_order)

        
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
        
        # Rename columns with the final axis
        self.df = self.df.rename_axis(columns=self.axes[-1])
            
    def save_dataset(self, append, key):
        """Save the collated dataset as an HDF file."""
        try:
            self.df.to_hdf(self.filename, append=append, key=key)
        except ValueError:
            self.df.to_hdf(self.filename, key=key)

    def close(self):
        """Close the browser instance."""
        self.driver.close()

    def run(self, close_immediately=True):
        """Create, clean, save the dataset, then optionally close browser."""
        self.create_dataset()
        self.clean_dataset()
        self.save_dataset(append=Path(self.filename).exists(), key=self.hdf_key)

        if close_immediately:
            self.close()
            print(
                f"Browser instance closed. Output file is saved at "
                f"{self.filename}."
            )
    
    def set_axes(self, axis_names):
        """Set the axes to specified names."""
        print(f"Setting axes to {axis_names}... ", end="")

        for i, name in enumerate(axis_names):
            self.menus[i].set_to(name)
            sleep(self.wait_time)

    def recalculate_tables(self):
        if self.webpage_type in ('object-whole', 'object-broken'):
            table_type = 'object'
        elif self.webpage_type in ('link-whole', 'link-broken'):
            table_type = 'link'
        self.tables = [Table(self.driver, i, table_type, self.wait_time) for i in range(3)]

    @staticmethod
    def get_axis_options(browser, url, headless):
        """Return a list of possible axis options for a particular URL."""
        # TODO: refactor validation to reduce code duplication
        # Check for valid browser
        if browser not in get_args(SUPPORTED_BROWSERS):
            msg = "browser must be one of the following: "
            msg += ', '.join(get_args(SUPPORTED_BROWSERS))
            raise TypeError(msg)
        
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
            
        # Get axis options
        driver = CollationEngine.get_driver(browser, headless)
        driver.get(url)
        webpage_type = WEBPAGE_TYPES[url]
        menu = AxisMenu(driver, webpage_type, 0, WAIT_TIME_FOR_POPULATION)

        options = menu.option_names

        driver.close()

        return options

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


## Main Block
if __name__ == '__main__':
    # If no options or arguments are provided, run with demo parameters
    if len(sys.argv) == 1:
        engine = CollationEngine(**STANDALONE_PARAMS)
        sys.exit()

    # Otherwise, run with the parameters from the command line
    #TODO: add validation for inputs
    user_opts = [a for a in sys.argv[1:] if "--" in a or "-" in a]
    user_args = [a for a in sys.argv[1:] if "--" not in a or "-" not in a]

    # Help
    if "--help" in user_opts or "-h" in user_opts:
        print(USAGE)
        sys.exit()

    # Browser validation
    try:
        browser = [i for i in user_opts if "browser" in i][0].replace(
            "--browser=", ""
        )
    except IndexError:
        print("Error: browser is a required option.")
        sys.exit()
    
    if browser not in get_args(SUPPORTED_BROWSERS):
        print(
            f"Error: browser must be one of the following: "
            f"{', '.join(get_args(SUPPORTED_BROWSERS))}"
        )
        sys.exit()
    
    # Other Validation
    if (1 <= len(user_opts) <= 3) and (len(user_args) in [0, 3]):
        # Options
        headless = len([i for i in user_opts if "headless" in i]) > 0
        optimize = len([i for i in user_opts if "optimize" in i]) > 0
    
        # Arguments
        if len(user_args) != 3:
            url = input("Please enter the URL of the TRAC webpage: ")
            file = input(
                "Please enter the name or path of the output file: "
            )
            axes = input(
                f"Please enter the axes of interest as a comma-separated "
                f"list: "
            ).replace('"', '').split(',')
        else:
            url = user_args[-3]
            file = user_args[-2]
            axes = user_args[-1].split(",")
        
        # Validate number of axes
        if len(axes) != 3:
            print("Error: three axes must be provided.")
            sys.exit()

        engine = CollationEngine(browser=browser, 
                                 url=url, 
                                 filename=file,
                                 axes=axes, 
                                 headless=headless, 
                                 optimize=optimize)
    
    # All other situations are incorrect usage
    else:
        print(
            f"Options or arguments not recognized. Type -h or --help for "
            f"usage details."
        )
