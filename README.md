# TRAC-Collation
This repository contains a tool for collating data published by the [Transactional Records Access Clearinghouse](https://trac.syr.edu/) (TRAC) in their [immigration toolkit](https://trac.syr.edu/immigration/tools/). This repository is still experimental, and files may change without much warning.

# Requirements
- selenium 4.17.0 (earlier might work but no guarantees)
- pandas 2.2.0 (earlier will probably work)
- tqdm

# Usage
1. Set up an environment with pandas and selenium (for conda instructions, see [here](https://conda.io/projects/conda/en/latest/user-guide/getting-started.html)).
2. Download/locate the webdriver for your browser of choice - currently [Firefox](https://github.com/mozilla/geckodriver/releases), [Chrome](https://chromedriver.chromium.org/downloads), [Edge](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/?form=MA13LH) and [Safari](https://developer.apple.com/documentation/webkit/testing_with_webdriver_in_safari) are supported. Add the webdriver's path to your environment variables (in the case of Firefox, for additional instructions see [here](https://www.browserstack.com/guide/geckodriver-selenium-python)).
3. Clone the repository, or just download `collate.py`.
4. Navigate to the TRAC webpage that you want to collate data from (to see if your tool is supported, check [below](#which-trac-tools-can-i-use-this-with)). Note the URL and the names of the axes you want to collate.
5. Open `collate.py`, navigate to the `if __name__ == '__main__'` block at the bottom, and set the parameters as follows:
  - `browser`: the name of the browser you downloaded that you downloaded the webdriver for.
  -  `url`: the address of the TRAC webpage that you want to collate data from, including the `https://` - for example, `https://trac.syr.edu/phptools/immigration/mpp4/`.
  - `filename`: the name of the HDF file (including the `.hdf` extension) you want the collated data to be saved in. Currently, only HDF file output is supported.
  - `axes`: the names of the three data axes you want to collate. In the final output dataest, values from the first two will be used as hierarchical indices, while values for the third will be used as columns. Support for more than three axes might be added later.
6. Run `collate.py` from the command line or your IDE.

Note: even when `collate.py` is used with supported TRAC tools, it is possible that it may occasionally throw `StaleElementReferenceException` or `NoSuchElementException` when the DOM changes unexpectedly or an element takes a while to load. Functionality that greatly limits such problems has been implemented - if this is a problem, you can try the following:
  - Try re-running on a better internet connecection.
  - Try re-running at a time when the TRAC servers are likely to have a low load (e.g., weekends, weekday evenings).
  - Try re-arranging your names in the `axes` parameter so that the third axis is the one with the greatest number of values. This will decrease both execution time and the required number of interaction events (i.e., clicks and waits), so it will decrease the number of opportunities for an element to not load in properly.

# Which TRAC tools can I use this with?
## Supported
Automated interaction with the following tools should be fully supported.
- [New Proceedings Filed in Immigration Court](https://trac.syr.edu/phptools/immigration/ntanew/)
- [Outcomes of Immigration Court Proceedings](https://trac.syr.edu/phptools/immigration/closure/)
- [Asylum Filings](https://trac.syr.edu/phptools/immigration/asyfile/)
- [Asylum Decisions](https://trac.syr.edu/phptools/immigration/asylum/)
- [MPP (Remain in Mexico) Deportation Proceedings—All Cases](https://trac.syr.edu/phptools/immigration/mpp4/)
- [Unaccompanied Juveniles — Immigration Court Deportation Proceedings](https://trac.syr.edu/phptools/immigration/juvenile/)
- [Priority Immigration Court Cases: Women with Children](https://trac.syr.edu/phptools/immigration/mwc/)
- [Border Patrol Arrests](https://trac.syr.edu/phptools/immigration/cbparrest/)
- [Stopping "Inadmissibles" at U.S. Ports of Entry](https://trac.syr.edu/phptools/immigration/cbpinadmiss/)
- [Immigration and Customs Enforcement Arrests](https://trac.syr.edu/phptools/immigration/arrest/)
- [Latest Data: Immigration and Customs Enforcement Detainers](https://trac.syr.edu/phptools/immigration/detain/)
- [Tracking Immigration and Customs Enforcement Detainers](https://trac.syr.edu/phptools/immigration/detainhistory/)
- [Latest Data: Immigration and Customs Enforcement Removals](https://trac.syr.edu/phptools/immigration/remove/)
- [Historical Data: Immigration and Customs Enforcement Removals](https://trac.syr.edu/phptools/immigration/removehistory/)
- [Removals under the Secure Communities Program](https://trac.syr.edu/phptools/immigration/secure/)

## Not yet supported
Automated interaction with the following tools is not supported. Some of these tools simply have an additional menu and are otherwise similar to the fully supported tools above, so you might have some success using `collate.py` with them. Others have totally different interfaces, and will not work at all with `collate.py`. Full support for these tools might be added later.
- [Immigration Court Backlog](https://trac.syr.edu/phptools/immigration/backlog/) - additional menu
- [Pending Court Cases by Immigrant’s Address](https://trac.syr.edu/phptools/immigration/addressrep/) - different interface
- [Judge-by-Judge Asylum Decisions in Immigration Courts](https://trac.syr.edu/immigration/reports/judgereports/) - different interface
- [Immigration Court Asylum Backlog](https://trac.syr.edu/phptools/immigration/asylumbl/) - additional menu
- [Immigration Court Bond Hearings and Related Case Decisions](https://trac.syr.edu/phptools/immigration/bond/) - different interface
- [Immigration and Customs Enforcement Detention](https://trac.syr.edu/phptools/immigration/detention/) - additional menu
- [Detention Facilities Average Daily Population](https://trac.syr.edu/immigration/detentionstats/facilities.html) - different interface
- [Alternatives to Detention (ATD)](https://trac.syr.edu/immigration/detentionstats/atd_pop_table.html) - different interface

# Disclaimer
This repository is intended to make federal immigration data more accessible to students, researchers, and journalists. It is not affiliated with, supported by, or recognized by TRAC. Always make sure to cite your sources properly. If you use this tool, I would appreciate an acknowledgement, but no citation is necessary.
