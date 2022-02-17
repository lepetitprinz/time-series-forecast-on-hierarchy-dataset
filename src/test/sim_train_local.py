import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from simulation.deployment.PipelineReal import PipelineReal

# Root path
path_root = os.path.join('/', 'opt', 'DF', 'fcst')
# path_root = os.path.join('..', '..')
date = {'history': {'from': '20190211', 'to': '20220206'}}
lag = 'w1'

# Configuration
exec_cfg = {
    'save_step_yn': True,               # Save object on local
    'scaling_yn': False,                # Data scaling
    'grid_search_yn': False,            # Grid Search
    'filter_threshold_week_yn': True    # Filter threshold week
}

# Step Configuration
step_cfg = {
    'cls_sim_load': True,    # Data Load
    'cls_sim_prep': True,     # Data Preprocessing
    'cls_sim_train': True     # Training
}

pipeline = PipelineReal(
    lag=lag,
    date=date,
    path_root=path_root,
    exec_cfg=exec_cfg,
    step_cfg=step_cfg
)

pipeline.run()
