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

TIMEOUT = 10

class Table:
    """A Table is a collection of Rows."""
    def __init__(self, web_element, table_type: Literal['object', 'link']):
        # Set instance attributes
        self.web_element = web_element
        self._rows = None
        self.table_type = table_type

    @property
    def rows(self):
        # Only calculate rows when asked to
        # https://stackoverflow.com/a/69379239/15426433
        if self._rows is None:
            self._rows = self.calculate_rows()
        return self._rows
    
    def calculate_rows(self):
        # Get elements for all rows
        wait = WebDriverWait(self.web_element, TIMEOUT)
        if self.table_type == 'object':
            row_elements = wait.until(EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, 'flex-row')
                )
            )
        elif self.table_type == 'link':
            row_elements = wait.until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, ".//tr")
                )
            )

        # Filter out meaningless elements
        def is_meaningful(text):
            return (text != '' and 'All' not in text and 'Total' not in text)
        text_rows = self.web_element.text.split('\n')

        text_indices_to_skip = [i for i, r in enumerate(text_rows) if not is_meaningful(r)]
        text_rows = [r for i, r in enumerate(text_rows) if i not in text_indices_to_skip]
        n_elements_to_skip = len(row_elements) - len(text_rows)
        row_elements = row_elements[n_elements_to_skip:]                  # currently, the skippable elements are always at the beginning, but this could change later

        print(f"{len(row_elements)=}, {len(text_rows)=}")   # TODO: come back here <---

        # Make a Row from each element
        return [Row(e, t, self.table_type) for e, t in zip(row_elements, text_rows)]

class Row:
    """A Row is clickable, and has a name and a value."""
    def __init__(self, web_element, text, table_type: Literal['object', 'link']):
        # Set instance attributes
        self.table_type = table_type
        self.web_element = web_element
        self.name, self.value = text.rsplit(' ', 1)
        self.value = int(self.value.replace(',', ''))
    
    def click(self):
        if self.table_type == 'object':
            self.web_element.click()
        elif self.table_type == 'link':
            wait = WebDriverWait(self.web_element, TIMEOUT)
            clickable_element = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, ".//td[@class='Data l']/a")
                )
            )
            clickable_element.click()
    

class CollationEngine():
    # For first implementation, user will specify three axes which will correspond
    # to the axes selected in the browser for the three tables (left to right).
    # In future versions, I want the user to be able to specify an arbitrary number
    # of axes, and have the engine construct a dataset that includes all of them.
    def __init__(self, url, filename, axes, headless: bool=False):
        # Initialize Driver
        options = Options()
        if headless:
            options.add_argument('--headless')
        self.driver = Firefox(options=options)
        self.driver.get(url)

        self.filename = filename
        self.axes = axes
        self.tables = [None, None, None]


        # Determine webpage type
        self.webpage_type = WEBPAGE_TYPES[url]

        # Calculate axes and tables
        self.calculate_menus()
        self.set_axes()
  
        self.create_dataset()
        self.clean_dataset()
        self.save_dataset()
    
        # close browser
        sleep(10)
        self.driver.close()

    def calculate_menus(self):
        wait = WebDriverWait(self.driver, TIMEOUT)

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
                wait = WebDriverWait(self.driver, TIMEOUT)
                menu = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//ul[starts-with(@id, 'headlessui-listbox-options')]")
                    )
                )

                wait = WebDriverWait(menu, TIMEOUT)
                option = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, f".//*[@role='option']/li/span[text()='{self.axes[i]}']")
                    )
                )
                option.click()
                
        elif 'link' in self.webpage_type:
            for i, menu in enumerate(self.menus):
                wait = WebDriverWait(menu, TIMEOUT)
                option = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, f".//option[.='{self.axes[i]}']")
                    )
                )
                option.click()

    def calculate_tables(self, indices):
        if 'object' in self.webpage_type:
            class_name = 'table-fixed'
            table_type = 'object'
        elif 'link' in self.webpage_type:
            class_name = 'Table'
            table_type = 'link'

        wait = WebDriverWait(self.driver, TIMEOUT)
        table_elements = wait.until(     
            EC.presence_of_all_elements_located((By.CLASS_NAME, class_name))
        )

        for i in indices:
            self.tables[i] = Table(table_elements[i], table_type)                  #only refresh the tables we need to
    
    def create_dataset(self):
        self.calculate_tables([0])
        
        data = {}

        for t1_row in self.tables[0].rows:
            print()
            data[t1_row.name] = {}
            t1_row.click()
            self.calculate_tables([1])

            for t2_row in self.tables[1].rows:    
                t2_row.click()
                self.calculate_tables([2])
                data[t1_row.name][t2_row.name] = {
                    r.name: r.value for r in self.tables[2].rows
                }
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

        # Sort df
        self.df = self.df.sort_index()

        # Add a Total Column
        self.df['Total'] = self.df.sum(axis=1)

        # Convert all floats to int (cannot have fractions of people)
        float_cols = self.df.select_dtypes(include=['float64'])
        for col in float_cols.columns.values:
            self.df[col] = self.df[col].astype('int64')

        # TODO: rename indices to reflect axis names
            
    def save_dataset(self):
        self.df.to_hdf(self.filename, key='TRACDataset')



if __name__ == '__main__':
    engine = CollationEngine(
        'https://trac.syr.edu/phptools/immigration/asylum/',
        # 'https://trac.syr.edu/phptools/immigration/cbparrest/',
        'test.hdf',
        axes=['Custody', 'Represented', 'Decision']
        # axes=['Child/Family Group', 'Special Initiatives', 'BP Disposition']
    )