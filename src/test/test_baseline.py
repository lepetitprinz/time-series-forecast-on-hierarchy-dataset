from baseline.deployment.Pipeline import Pipeline

# Sales Data configuration
division = 'SELL_IN'

# Level Configuration
lvl_cfg = {
    'cust_lvl': 0,   # Customer group - Customer
    'item_lvl': 5    # Biz - Line - Brand - Item - SKU
}
# Data IO Configuration
io_cfg = {
    'save_step_yn': False,
    'save_db_yn': False,
    'decompose_yn': False
}

# Execute Configuration
exec_cfg = {
    'cls_load': False,
    'cls_cns': False,
    'cls_prep': True,
    'cls_train': False,
    'cls_pred': False
}

pipeline = Pipeline(division=division,
                    lvl_cfg=lvl_cfg,
                    io_cfg=io_cfg,
                    exec_cfg=exec_cfg)

# Execute Baseline Forecast
pipeline.run()

