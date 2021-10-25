from dao.DataIO import DataIO

import numpy as np
import pandas as pd
from datetime import datetime
from statsmodels.tsa.seasonal import seasonal_decompose


class Decomposition(object):
    def __init__(self, common, division: str, hrchy_list: list, hrchy_lvl_cd: str, date_range):
        self.dao = DataIO()
        self.date_range = date_range
        self.division = division
        self.hrchy_list = hrchy_list
        self.hrchy_lvl_cd = hrchy_lvl_cd
        self.x = common['target_col']
        self.model = 'additive'     # additive / multiplicative
        self.tb_name = 'M4S_O110500'
        self.save_to_db_yn = True

    def decompose(self, df):
        data = pd.Series(data=df[self.x].to_numpy(), index=df.index)

        data_resampled = data.resample(rule='W').sum()
        # data_resampled = data.resample(rule='D').sum()

        if len(data_resampled.index) != len(self.date_range):
            idx_add = list(set(self.date_range) - set(data_resampled.index))
            data_add = np.zeros(len(idx_add))
            df_add = pd.Series(data_add, index=idx_add)
            data_resampled = data_resampled.append(df_add)
            data_resampled = data_resampled.sort_index()

        data_resampled = data_resampled.fillna(0)

        # Seasonal Decomposition
        decomposed = seasonal_decompose(x=data_resampled, model=self.model)
        item_info = df[self.hrchy_list].drop_duplicates()
        item_info = item_info.iloc[0].to_dict()
        result = pd.DataFrame(
            {'project_cd': 'ENT002',
             'division_cd': self.division,
             'hrchy_lvl_cd': self.hrchy_lvl_cd,
             'item_attr01_cd': item_info.get('biz_cd', np.nan),
             'item_attr02_cd': item_info.get('line_cd', np.nan),
             'item_attr03_cd': item_info.get('brand_cd', np.nan),
             'item_attr04_cd': item_info.get('item_cd', np.nan),
             'yymmdd': [datetime.strftime(dt, '%Y%m%d') for dt in list(data_resampled.index)],
             'org_val': decomposed.observed,
             'trend_val': decomposed.trend.fillna(0),
             'seasonal_val': decomposed.seasonal.fillna(0),
             'resid_val': decomposed.resid.fillna(0),
             'create_user_cd': 'SYSTEM',
             'create_date': datetime.now()})

        # Save
        if self.save_to_db_yn:
            self.dao.insert_to_db(df=result, tb_name=self.tb_name)
