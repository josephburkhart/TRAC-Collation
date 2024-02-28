# TRAC-Collation
This repository contains some notebooks for collating data from several data publication tools managed by the Transactional Records Access Clearinghouse (TRAC). This repository is very experimental, and files may change significantly without warning. In the future, I may refactor the notebooks into a proper module or package.

# Requirements
- selenium 4.17.0 (earlier might work but no guarantees)
- pandas 2.2.0 (earlier will probably work)

# Contents
- `sandbox_allimmigrationcourtdecisions.ipynb`: notebook used for collating data from https://trac.syr.edu/phptools/immigration/closure/
- `sandbox_asylumdecisions.ipynb`: notebook used for collating data from https://trac.syr.edu/phptools/immigration/asylum/
- `sandbox_asylumfilings.ipynb`: notebook used for collating data from https://trac.syr.edu/phptools/immigration/asyfile/
- `sandbox_iceremovals.ipynb`: notebook used for collating data from https://trac.syr.edu/phptools/immigration/remove/
- `collate.py`: contains class for more general collation