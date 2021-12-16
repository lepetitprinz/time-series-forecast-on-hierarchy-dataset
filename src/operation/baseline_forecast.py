import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from baseline.deployment.PipelineTest import PipelineTest

# Sales Data configuration
division = 'SELL_IN'    # SELL_IN / SELL_OUT
in_out = 'out'    # SELL-IN : out / in
cycle = 'w'    # SELL-OUT : w(week) / m(month)

test_vrsn_cd = 'CRONTAB_TEST'

# Data Configuration
data_cfg = {
    'division': division,
    'in_out': in_out,
    'cycle': cycle,
    'test_vrsn_cd': test_vrsn_cd
}

# Level Configuration
lvl_cfg = {
    'cust_lvl': 1,   # SP1
    'item_lvl': 3,    # Biz - Line - Brand - Item - SKU
}
# Configuration
exec_cfg = {
    'save_step_yn': True,            # Save each step result to object or csv
    'save_db_yn': False,             #
    'rm_not_exist_lvl_yn': False,    # Remove not exist data level
    'decompose_yn': False,           # Decomposition
    'scaling_yn': False,             # Data scaling
    'impute_yn': True,               # Data Imputation
    'rm_outlier_yn': True,           # Outlier Correction
    'feature_selection_yn': False,   # Feature Selection
    'grid_search_yn': False          # Grid Search
}

# Execute Configuration
step_cfg = {
    'cls_load': True,
    'cls_cns': True,
    'cls_prep': True,
    'cls_train': True,
    'cls_pred': True,
    'clss_mdout': True,
    'cls_rpt': True
}

# Load result configuration
exec_rslt_cfg = {
    'train': False,
    'predict': False,
    'middle_out': False
}

# Unit Test Option
unit_cfg = {
    'unit_test_yn': False,
    'cust_grp_cd': '1202',
    'item_cd': '5100000'
}

pipeline = PipelineTest(
    data_cfg=data_cfg,
    lvl_cfg=lvl_cfg,
    exec_cfg=exec_cfg,
    step_cfg=step_cfg,
    exec_rslt_cfg=exec_rslt_cfg,
    unit_cfg=unit_cfg
)

# Execute Baseline Forecast
# pipeline.run()