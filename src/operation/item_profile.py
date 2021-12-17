import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from recommend.deployment.PipelineCycle import PipelineCycle

cfg = {
    'save_step_yn': True,            # Save each step result to object or csv
    'save_db_yn': True,             #
    'cycle': 'w'
}

pipeline = PipelineCycle(cfg=cfg)
pipeline.run()
