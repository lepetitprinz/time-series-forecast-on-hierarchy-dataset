import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from baseline.deployment.PipelineVerify import PipelineVerify

# Path configuration
path_root = os.path.join('/', 'opt', 'DF', 'fcst')

# Configuration
exec_cfg = {
    'cycle': True,                           # Prediction cycle

    # save configuration
    'save_step_yn': True,                    # Save each step result to object or csv
    'save_db_yn': False,                     # Save each step result to Database

    # Data preprocessing configuration
    'decompose_yn': False,                   # Decomposition
    'rolling_statistics_yn': True,           # Rolling Statistics(Average/Median/Min/Max)
    'feature_selection_yn': False,           # Feature Selection
    'filter_threshold_cnt_yn': False,        # Filter data level under threshold count
    'filter_threshold_recent_yn': True,      # Filter data level under threshold recent week
    'filter_threshold_recent_sku_yn': True,  # Filter SKU level under threshold recent week
    'rm_fwd_zero_sales_yn': True,            # Remove forward empty sales
    'rm_outlier_yn': True,                   # Outlier Correction
    'data_imputation_yn': True,              # Data Imputation

    # Training configuration
    'scaling_yn': False,                     # Data scaling
    'grid_search_yn': False,                 # Grid Search
}

# Execute Configuration
step_cfg = {
    'cls_load': False,
    'cls_cns': False,
    'cls_prep': True,
    'cls_train': True,
    'cls_pred': True,
    'cls_mdout': True,
    'cls_acc': True
}

# Data Configuration
data_cfg = {
    'division': 'SELL_IN',
    'apply_num_work_day': False
}

pipeline = PipelineVerify(
    data_cfg=data_cfg,
    exec_cfg=exec_cfg,
    step_cfg=step_cfg,
    path_root=path_root
)
# Execute Baseline Forecast (Sell-in)
pipeline.run()

# Data Configuration
data_cfg = {
    'division': 'SELL_OUT',
    'apply_num_work_day': False
}

pipeline = PipelineVerify(
    data_cfg=data_cfg,
    exec_cfg=exec_cfg,
    step_cfg=step_cfg,
    path_root=path_root
)
# Execute Baseline Forecast (Sell-out)
pipeline.run()