import pytest
from pathlib import Path
from collate import CollationEngine, SUPPORTED_BROWSERS
from typing import get_args
import pandas as pd

SINGLE_DATASETS = [
    # (
    #     "https://tracreports.org/phptools/immigration/asyfile/", 
    #     ["Fiscal Year Application Filed", "How Long in U.S.", "Gender"], 
    #     Path("control/2025-02_AsylumFilings_FiscalYearApplicationFiled-HowLongInUS-Gender.hdf")
    # ),
    (
        "https://tracreports.org/phptools/immigration/asylum/", 
        ["Decision", "Age", "Absentia"], 
        Path("control/2025-02_AsylumDecisions_Decision-Age-Absentia.hdf")
    ),
    # (
    #     "https://tracreports.org/phptools/immigration/mwc/", 
    #     ["Fiscal Year Case Began", "Outcome", "Represented"], 
    #     Path("control/2025-02_WomenWithChildren_FiscalYearCaseBegan-Outcome-Represented.hdf")
    # ),
    # (
    #     "https://tracreports.org/phptools/immigration/cbparrest/", 
    #     ["Arrest Method", "Time in U.S.", "Gender"], 
    #     Path("control/2025-02_BordrePatrolArrests_ArrestMethod-TimeInUS-Gender.hdf")
    # ),
]

def single_dataset_test(browser, headless, optimize, url, axes, control_file_path, tmp_path):
    """Ensure that HDF files containing single datasets are consistent with 
    control files generated by hand."""
    test_file_path = tmp_path / f"{url.split("/")[-2]}_{"-".join(axes).replace(" ", "")}.hdf"
    hdf_key = "; ".join(axes)
    engine = CollationEngine(browser, url, test_file_path, axes, headless, 
                             optimize, hdf_key)
    
    test_file_df = pd.read_hdf(test_file_path)
    control_file_df = pd.read_hdf(control_file_path)

    pd.testing.assert_frame_equal(control_file_df, test_file_df)

@pytest.mark.parametrize("headless", [False, True])
@pytest.mark.parametrize("optimize", [False, True])
@pytest.mark.parametrize("url,axes,control_file_path", SINGLE_DATASETS)
def test_firefox_single_datasets(headless, optimize, url, axes, control_file_path, tmp_path):
    single_dataset_test("Firefox", headless, optimize, url, axes, control_file_path, tmp_path)

@pytest.mark.parametrize("headless", [False, True])
@pytest.mark.parametrize("optimize", [False, True])
@pytest.mark.parametrize("url,axes,control_file_path", SINGLE_DATASETS)
def test_chrome_single_datasets(headless, optimize, url, axes, control_file_path, tmp_path):
    single_dataset_test("Chrome", headless, optimize, url, axes, control_file_path, tmp_path)

@pytest.mark.parametrize("headless", [False, True])
@pytest.mark.parametrize("optimize", [False, True])
@pytest.mark.parametrize("url,axes,control_file_path", SINGLE_DATASETS)
def test_edge_single_datasets(headless, optimize, url, axes, control_file_path, tmp_path):
    single_dataset_test("Edge", headless, optimize, url, axes, control_file_path, tmp_path)

# def test_safari_single_datasets(headless, optimize, url, axes, control_file_path, tmp_path):
#     # Note: If System is not a mac, Safari can't be installed, so we need to short-
#     #       circuit the test for Safari
#     single_dataset_test("Safari", headless, optimize, url, axes, control_file_path, tmp_path)

# def test_multiple_datasets():
#     # ensure that we can properly append multiple dataframes to a single HDF
#     pass

# def test_cli():
#     pass