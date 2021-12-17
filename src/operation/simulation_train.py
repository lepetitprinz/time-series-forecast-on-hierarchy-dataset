import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from simulation.deployment.PipelineCycle import PipelineCycle

# Configuration
exec_cfg = {
    'save_step_yn': True,
    'scaling_yn': False,     # Data scaling
    'grid_search_yn': False    # Grid Search
}

# Step Configuration
step_cfg = {
    'cls_sim_load': False,
    'cls_sim_prep': True,
    'cls_sim_train': True
}

pipeline = PipelineCycle(
    exec_cfg=exec_cfg,
    step_cfg=step_cfg,
)

# pipeline.run()
