> [!WARNING]
> ~~**2025-01-22:** As of January 2025, the Transactional Records Access Clearinghouse has left Syracuse University and its website has been taken offline, rendering this tool useless. If the website is put back up, or if a successor takes up TRAC's mantle, please file an [issue](https://github.com/josephburkhart/TRAC-Collation/issues/new?q=sort%3Aupdated-desc+is%3Aissue+is%3Aopen&template=Blank+issue) on this repository and I'll update the tool to work with the new website.~~
>
> ~~**2025-02-12:** As of early February 2025, The Transactional Records Access Clearinghouse has restored part of their website at a new address: https://tracreports.org. I am working to update this tool to work with the new website.~~
>
> ~~**2025-02-12:** As of February 12, 2025, I have updated `collate.py` to work with TRAC's new website. Some of TRAC's tools are still not online (see [below](#which-trac-tools-can-i-use-this-with)). Please file an [issue](https://github.com/josephburkhart/TRAC-Collation/issues/new?q=sort%3Aupdated-desc+is%3Aissue+is%3Aopen&template=Blank+issue) if the tool is not working properly.~~
>
> ~~**2025-02-18:** I have found a bug that can silently cause errors in the saved datasets when using Chrome and Edge - Firefox seems unaffected. I am working on a solution. In the meantime, please use Firefox or wait for me to implement a solution.~~
> 
> **2025-02-25:**, I have resolved the remaining bugs caused by TRAC's new website. In the process, I have had to drop support for Firefox and Safari. If you used this tool between February 1 and February 25, your dataset may contain errors, so you should pull down or copy the latest version of `collate.py` and use it to refresh your dataset. As always, please file an [issue](https://github.com/josephburkhart/TRAC-Collation/issues/new?q=sort%3Aupdated-desc+is%3Aissue+is%3Aopen&template=Blank+issue) if you think this tool is not working properly.

# TRAC-Collation
This repository contains a tool for collating data published by the [Transactional Records Access Clearinghouse](https://tracreports.org/) (TRAC) in their [immigration toolkit](https://tracreports.org/immigration/tools/).

# Requirements
- selenium 4.17.0 (earlier might work but no guarantees)
- pandas 2.2.0 (earlier will probably work)
- tqdm

# Usage
1. Set up an environment with pandas and selenium (for conda instructions, see [here](https://conda.io/projects/conda/en/latest/user-guide/getting-started.html)).
2. Download/locate the webdriver for your browser of choice - currently [Chrome](https://chromedriver.chromium.org/downloads) abd [Edge](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/?form=MA13LH) are supported. Add the webdriver's path to your environment variables, or put the executable file in the same folder as `collate.py`.
3. Clone the repository, or just download `collate.py`.
4. Navigate to the TRAC webpage that you want to collate data from (to see if your tool is supported, check [below](#which-trac-tools-can-i-use-this-with)). Note the URL and the names of the axes you want to collate.
5. `collate.py` can be run from an IDE or the command line:
  - To run in an IDE, open `collate.py`, navigate to `STANDALONE_PARAMS`, and set the following values:
    - `browser`: the name of the browser you downloaded that you downloaded the webdriver for.
    -  `url`: the address of the TRAC webpage that you want to collate data from, including the `https://` - for example, `https://tracreports.org/phptools/immigration/mpp4/`.
    - `filename`: the name of the HDF file (including the `.hdf` extension) you want the collated data to be saved in. Currently, only HDF file output is supported.
    - `axes`: the names of the three data axes you want to collate. In the final output dataest, values from the first two will be used as hierarchical indices, while values for the third will be used as columns. Support for more than three axes might be added later.
    - `headless`: whether or not to run your browser in headless mode, which hides the window.
    - `optimize`: whether or not to optimize the data traversal path to minimize the number of clicks and waits.
  - To run from the command line, ensure that your conda environment is active and that `collate.py` is in your current directory. There are three ways to run `collate.py` from the command line:
    - `python collate.py` runs the script with the standalone parameters.
    - `python collate.py <options>` runs the script with options. The user will then be prompted for the arguments individually. Options are:
      - `--browser=<name>`: name of the browser to use. Valid names are `Firefox`, `Chrome`, `Edge`, and `Safari`.
      - `--headless`: use the browser in headless mode. (This option is not required.)
      - `--optimize`: optimize data traversal for fewest clicks and waits. (This option is not required.)
      - `-h` or `--help`: show usage details. (This option is not required.)
    - `python collate.py <options> <arguments>` runs the script with options and arguments. Arguments are:
      - `url`: full address of the TRAC webpage
      - `file`: name or full path of the output file. Equivalent to `filename` in `STANDALONE_PARAMS`.
      - `axes`: Comma-separated list of the names of the axes of interest. Note that the list must be enclosed in "" if any names include spaces.

Note: even when `collate.py` is used with supported TRAC tools, it is possible that it may occasionally throw `StaleElementReferenceException` or `NoSuchElementException` when the DOM changes unexpectedly or an element takes a while to load. The code has been structured to greatly limit such problems, but if you are still having trouble you can try the following:
  - Try re-running on a faster internet connecection.
  - Try re-running at a time when the TRAC servers are likely to have a low load (e.g., weekends, weekday evenings).
  - Pass the `optimize` flag to minimize the number of clicks and waits.

# Which TRAC tools can I use this with?
## Supported
Automated interaction with the following tools should be fully supported.
- [New Proceedings Filed in Immigration Court](https://tracreports.org/phptools/immigration/ntanew/)
- [Outcomes of Immigration Court Proceedings](https://tracreports.org/phptools/immigration/closure/)
- [Asylum Filings](https://tracreports.org/phptools/immigration/asyfile/)
- [Asylum Decisions](https://tracreports.org/phptools/immigration/asylum/)
- [MPP (Remain in Mexico) Deportation Proceedings—All Cases](https://tracreports.org/phptools/immigration/mpp4/)
- [Unaccompanied Juveniles — Immigration Court Deportation Proceedings](https://tracreports.org/phptools/immigration/juvenile/)
- [Priority Immigration Court Cases: Women with Children](https://tracreports.org/phptools/immigration/mwc/)
- [Border Patrol Arrests](https://tracreports.org/phptools/immigration/cbparrest/)
- [Stopping "Inadmissibles" at U.S. Ports of Entry](https://tracreports.org/phptools/immigration/cbpinadmiss/)
- [Immigration and Customs Enforcement Arrests](https://tracreports.org/phptools/immigration/arrest/)
- ~~[Latest Data: Immigration and Customs Enforcement Detainers](https://tracreports.org/phptools/immigration/detain/)~~ _Not on the new website as of February 12, 2025_
- ~~[Tracking Immigration and Customs Enforcement Detainers](https://tracreports.org/phptools/immigration/detainhistory/)~~ _Not on the new website as of February 12, 2025_
- [Latest Data: Immigration and Customs Enforcement Removals](https://tracreports.org/phptools/immigration/remove/)
- [Historical Data: Immigration and Customs Enforcement Removals](https://tracreports.org/phptools/immigration/removehistory/)
- [Removals under the Secure Communities Program](https://tracreports.org/phptools/immigration/secure/)

## Not yet supported
Automated interaction with the following tools is not supported. Some of these tools simply have an additional menu and are otherwise similar to the fully supported tools above, so you might have some success using `collate.py` with them. Others have totally different interfaces, and will not work at all with `collate.py`. Full support for these tools might be added later.
- [Immigration Court Backlog](https://tracreports.org/phptools/immigration/backlog/) - additional menu
- [Pending Court Cases by Immigrant’s Address](https://tracreports.org/phptools/immigration/addressrep/) - different interface
- [Judge-by-Judge Asylum Decisions in Immigration Courts](https://tracreports.org/immigration/reports/judgereports/) - different interface
- [Immigration Court Asylum Backlog](https://tracreports.org/phptools/immigration/asylumbl/) - additional menu
- [Immigration Court Bond Hearings and Related Case Decisions](https://tracreports.org/phptools/immigration/bond/) - different interface
- [Immigration and Customs Enforcement Detention](https://tracreports.org/phptools/immigration/detention/) - additional menu
- [Detention Facilities Average Daily Population](https://tracreports.org/immigration/detentionstats/facilities.html) - different interface
- [Alternatives to Detention (ATD)](https://tracreports.org/immigration/detentionstats/atd_pop_table.html) - different interface

# Disclaimer
This repository is intended to make federal immigration data more accessible to students, researchers, and journalists. It is not affiliated with, supported by, or recognized by TRAC. Always make sure to cite your sources properly. If you use this tool, I would appreciate an acknowledgement, but no citation is necessary.
