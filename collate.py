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
from typing import Literal
import pandas as pd
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Browser-specific imports
# TODO: conditional import based on user's choice of browser
from selenium.webdriver import Firefox                  
from selenium.webdriver.firefox.options import Options

# WEBDRIVER_PATH = None
WEBPAGE_TYPES = {
    'https://trac.syr.edu/phptools/immigration/closure/': 'object-whole',
    'https://trac.syr.edu/phptools/immigration/backlog/': 'object-broken',
    'https://trac.syr.edu/phptools/immigration/asylum/': 'object-unified',
    'https://trac.syr.edu/phptools/immigration/asylumbl/': 'object-broken',
    'https://trac.syr.edu/phptools/immigration/cbparrest/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/remove/': 'link-whole',
    'https://trac.syr.edu/phptools/immigration/detention/': 'link-broken'
}

class CollationEngine():
    # For first implementation, user will specify three axes which will correspond
    # to the axes selected in the browser for the three tables (left to right).
    # In future versions, I want the user to be able to specify an arbitrary number
    # of axes, and have the engine construct a dataset that includes all of them.
    def __init__(self, url, filename, axes, headless: bool=False, timeout=10):
        # Initialize Driver
        options = Options()
        if headless:
            options.add_argument('--headless')
        self.driver = Firefox(options=options)
        self.driver.get(url)

        self.timeout = timeout
        self.axes = axes

        # Determine webpage type
        self.webpage_type = WEBPAGE_TYPES[url]

        # Calculate axes and tables
        self.calculate_tables()
        self.calculate_menus()
        self.set_axes()

        # close browser
        sleep(10)
        self.driver.close()

    def calculate_menus(self):
        wait = WebDriverWait(self.driver, self.timeout)

        #TODO: account for object-broken and link-broken
        if 'object' in self.webpage_type:
            self.menus = wait.until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//button[starts-with(@id, 'headlessui-listbox-button')]")
                )
            )
        elif 'link' in self.webpage_type:
            self.menus = wait.until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//select[starts-with(@id, 'dimension_pick')]")
                )
            )
    
    def set_axes(self):
        if 'object' in self.webpage_type:
            # Note: for webpages of this type, menus that were previously calculated are actually buttons to open the menus
            for i, menu in enumerate(self.menus):
                menu.click()
                wait = WebDriverWait(self.driver, self.timeout)
                menu = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//ul[starts-with(@id, 'headlessui-listbox-options')]")
                    )
                )

                wait = WebDriverWait(menu, self.timeout)
                option = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, f".//*[@role='option']/li/span[text()='{self.axes[i]}']")
                    )
                )
                option.click()
                
        elif 'link' in self.webpage_type:
            for i, menu in enumerate(self.menus):
                wait = WebDriverWait(menu, self.timeout)
                option = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, f".//option[.='{self.axes[i]}']")
                    )
                )
                option.click()

    def calculate_tables(self):
        if 'object' in self.webpage_type:
            name = 'table-fixed'
        elif 'link' in self.webpage_type:
            name = 'Table'

        #TODO: check that order of tables in list is left to right in browser
        wait = WebDriverWait(self.driver, self.timeout)
        self.tables = wait.until(     
            EC.presence_of_all_elements_located((By.CLASS_NAME, name))
        )
    
    def parse_table(self, table, into: Literal['text_rows', 'clickable_rows']):
        if into == 'text_rows':
            rows = [r.rsplit(' ', 1) for r in table.text.split('\n')]           #note: skip first two rows
            rows = [r for r in rows if r != '' and r.find('All') == -1]         #note: several blank rows and a total row are always at the top
            rows = [[r[0], r[1].replace(',', '')] for r in rows]
        
        elif into =='clickable_rows':
            wait = WebDriverWait(table, self.timeout)
            if 'object' in self.webpage_type:
                rows = wait.until(
                    EC.presence_of_all_elements_located(
                        (By.CLASS_NAME, 'flex-row')
                    )
                )
                rows = [r for r in rows if r.text != '' and r.text.find('All') == -1]  

            elif 'link' in self.webpage_type:
                rows = wait.until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, ".//tr/td[@class='Data l']/a")   #note: may change in the future
                    )
                )
        return rows

    def write_entry_to_temp_file(self):
        pass

    def write_page_to_hdf(self):
        pass


