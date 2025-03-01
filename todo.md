- [x] move table and row functionality into separate Table class
- [x] add validation for user input
- [x] add command line interface (maybe including progress bar)
- [x] add support for other browsers (will probably require a config file)
- [x] add try-except blocks to catch stale reference exceptions and the like
- [x] add an optimize flag to CollateEngine.__init__ to indicate whether we should solve for the path through the specified axes that minimizes the number of total clicks/waits
- [ ] figure out why expected and actual table totals sometimes just don't add up (currently, we detect those cases and just raise a RuntimeError)
- [ ] create a decorator to wrap the while-try-except functionality, which is currently duplicated across many methods
- [ ] add support for other webpage types:

| URL                                                                   | Webpage Type    | Comments                                                                                                                    |
|-----------------------------------------------------------------------|-----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| https://tracreports.org/phptools/immigration/ntanew/                  | object-broken-1 | 1 additional axis (2 possible values)                                                                                                                       |
| https://tracreports.org/phptools/immigration/closure/                 | object-broken-1 | 3 additional axes (2, 2, 6 possible values)                                                                                                                 |
| https://tracreports.org/phptools/immigration/backlog/                 | object-broken-2 | 4 additional axes? two of them seem bound together (14, 2, 3 possible   values)                                                                             |
| https://tracreports.org/phptools/immigration/addressrep/              | map-table       | very different interface, have to click on svg objects and then click   back button (50 possible states, 2 possible state subdivisions, 1 table for   each) |
| https://tracreports.org/immigration/reports/judgereports/             | table-only-1    | simple - just copy the table once                                                                                                                           |
| https://tracreports.org/phptools/immigration/asylumbl/                | object-broken-2 | 3 additional axes? two of them seem bound together (13, 3 possible   values)                                                                                |
| https://tracreports.org/phptools/immigration/bond/                    | table-tab       | 1 additional axis (2 possible values), 2 meaningful tabs                                                                                                    |
| https://tracreports.org/phptools/immigration/detention/               | link-broken     | 1 additional axis (17 possible values) - total of 680 * 17 = 11,560   possible combinations!                                                                |
| https://tracreports.org/immigration/detentionstats/facilities.html    | table-only-2    | simple - just copy the table once                                                                                                                           |
| https://tracreports.org/immigration/detentionstats/atd_pop_table.html | table-only-2    | simple - just copy the table once 


- [ ] investigate why everything.py fails with the following:
    - asyfile: 
        - ('Month and Year Application Filed', 'Immigration Court', 'Nationality')
        - ('Month and Year Application Filed', 'Immigration Court', 'Language')
        - ('Fiscal Year Application Filed', 'Immigration Court', 'Hearing Attendance')
        - ('Fiscal Year Application Filed', 'Language', 'Custody')
    - asylum:
        - ('Month and Year of Decision', 'Immigration Court State', 'Immigration Court')
        - ('Month and Year of Decision', 'Immigration Court State', 'Language')
        - Note: these all seem to work solo, but note that they all have excessive numbers of rows. In at least some cases, e.g. ('Month and Year of Decision', 'Immigration Court State', 'Immigration Court'), this is needlessly large, because one axis actually only has one or two values for each unique value of the other - 'Immigration Court' and 'Immigration Court State'. 
            - One easy fix might be to just keep re-calling scrape() on the url until all of the axes worked
            - Another less-easy fix would be to improve the optimization process. Instead of just arranging axes from lowest number of individual values to highest, we would instead see how many options each axis would have for each value of each other axis, then take the average of those numbers and...
            - Update: I have now implemented both of these fixes
    - mpp4: 
        - can't even get started - first set of axes should be ('Fiscal Year Case Began', 'Month and Year Case Began', 'New MPP Case Since Jan 2021')
            - it works fine in solo testing - maybe I just can't have more than 1 or 2 browser instances going.
            - Let's test by running everything.py with just this url --> that works
            - Let's test by running everything.py with just this and one other url --> that also works
            - Ok, so that probably means that on Tuikku, I should only try to parallelize to 2 URLs at a time