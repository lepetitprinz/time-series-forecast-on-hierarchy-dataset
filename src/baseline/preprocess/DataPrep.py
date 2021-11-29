from baseline.analysis.Decomposition import Decomposition
from baseline.feature_engineering.FeatureEngineering import FeatureEngineering
import common.util as util

import numpy as np
import pandas as pd
from copy import deepcopy
from sklearn.impute import KNNImputer


class DataPrep(object):
    DROP_COLS_DATA_PREP = ['division_cd', 'seq', 'from_dc_cd', 'unit_price', 'create_date']
    STR_TYPE_COLS = ['cust_grp_cd', 'sku_cd']

    def __init__(self, date: dict, division: str, common: dict,
                 hrchy: dict, exec_cfg: dict):
        # Dataset configuration
        self.exec_cfg = exec_cfg
        self.division = division
        self.common = common
        self.date_col = common['date_col']
        self.resample_rule = common['resample_rule']
        self.col_agg_map = {
            'sum': common['agg_sum'].split(','),
            'avg': common['agg_avg'].split(',')
        }
        self.date_range = pd.date_range(
            start=date['date_from'],
            end=date['date_to'],
            freq=common['resample_rule']
        )
        self.sales_recent = None
        # Exogenous variable map
        self.exg_map = {
            '1202': '108',
            '1005': '108',
            '1033': '159',
            '1212': '279',
            '1067': '999'
        }
        # Hierarchy configuration
        self.hrchy = hrchy
        self.hrchy_level = hrchy['lvl']['cust'] + hrchy['lvl']['item'] - 1

        # Execute option
        self.imputer = 'knn'
        self.sigma = 2.5
        self.outlier_method = 'std'
        self.quantile_range = 0.02

    def preprocess(self, data: pd.DataFrame, exg: pd.DataFrame) -> tuple:
        # ------------------------------- #
        # 0. Remove sales
        # ------------------------------- #
        if self.exec_cfg['rm_not_exist_lvl_yn']:
            pass


        # ------------------------------- #
        # 1. Preprocess sales dataset
        # ------------------------------- #
        exg_list = list(idx.lower() for idx in exg['idx_cd'].unique())

        # convert data type
        for col in self.STR_TYPE_COLS:
            data[col] = data[col].astype(int).astype(str)

        # convert datetime column
        data[self.date_col] = data[self.date_col].astype(np.int64)

        # 2. Preprocess Exogenous dataset
        exg = util.prep_exg_all(data=exg)

        # Merge sales data & exogenous(all) data
        data = self.merge_exg(data=data, exg=exg)

        # preprocess sales dataset
        data = self.conv_data_type(df=data)

        # Feature engineering
        if self.exec_cfg['feature_selection_yn']:
            fe = FeatureEngineering(
                common=self.common,
                exg_list=exg_list
            )
            data, exg_list = fe.feature_selection(data=data)

        # Grouping
        data_group, hrchy_cnt = util.group(hrchy=self.hrchy['apply'], hrchy_lvl=self.hrchy_level, data=data)

        # Decomposition
        if self.exec_cfg['decompose_yn']:
            decompose = Decomposition(
                common=self.common,
                division=self.division,
                hrchy=self.hrchy,
                date_range=self.date_range
            )

            util.hrchy_recursion(
                hrchy_lvl=self.hrchy_level,
                fn=decompose.decompose,
                df=data_group
            )

            decompose.dao.session.close()

        # Check Missing Values
        # data_miss_rate = util.hrchy_recursion(
        #     hrchy_lvl=self.hrchy_level,
        #     fn=self.check_missiing_value,
        #     df=data_group
        # )

        print("Week Count: ", len(self.date_range))
        miss_rate = util.hrchy_recursion(
            hrchy_lvl=self.hrchy_level,
            fn=self.check_missiing_value,
            df=data_group
        )

        # Resampling
        data_resample = util.hrchy_recursion(
            hrchy_lvl=self.hrchy_level,
            fn=self.resample,
            df=data_group
        )

        return data_resample, exg_list, hrchy_cnt

    def rm_not_exist_sales(self, sales_hist, sales_recent):
        pass

    def merge_exg(self, data: pd.DataFrame, exg: dict):
        cust_grp_list = list(data['cust_grp_cd'].unique())

        merged = pd.DataFrame()
        for cust_grp in cust_grp_list:
            temp = data[data['cust_grp_cd'] == cust_grp]
            temp = pd.merge(temp, exg[self.exg_map[cust_grp]], on=self.date_col, how='left')
            merged = pd.concat([merged, temp])

        return merged

    def conv_data_type(self, df: pd.DataFrame) -> pd.DataFrame:
        # drop unnecessary columns
        df = df.drop(columns=self.__class__.DROP_COLS_DATA_PREP, errors='ignore')
        df['unit_cd'] = df['unit_cd'].str.replace(' ', '')
        # Convert unit code
        if self.division == 'SELL_IN':
            conditions = [df['unit_cd'] == 'EA',
                          df['unit_cd'] == 'BOL',
                          df['unit_cd'] == 'BOX']

            values = [df['box_ea'], df['box_bol'], 1]
            unit_map = np.select(conditions, values)
            df['qty'] = df['qty'].to_numpy() / unit_map

            df = df.drop(columns=['box_ea', 'box_bol'], errors='ignore')

        # convert to datetime
        df[self.date_col] = pd.to_datetime(df[self.date_col], format='%Y%m%d')
        df = df.set_index(keys=[self.date_col])

        # add noise feature
        # df = self.add_noise_feat(df=df)

        return df

    def group(self, data, cd=None, lvl=0) -> dict:
        grp = {}
        col = self.hrchy[lvl]

        code_list = None
        if isinstance(data, pd.DataFrame):
            code_list = list(data[col].unique())

        elif isinstance(data, dict):
            code_list = list(data[cd][col].unique())

        if lvl < self.hrchy_level:
            for code in code_list:
                sliced = None
                if isinstance(data, pd.DataFrame):
                    sliced = data[data[col] == code]
                elif isinstance(data, dict):
                    sliced = data[cd][data[cd][col] == code]
                result = self.group(data={code: sliced}, cd=code, lvl=lvl + 1)
                grp[code] = result

        elif lvl == self.hrchy_level:
            temp = {}
            for code in code_list:
                sliced = None
                if isinstance(data, pd.DataFrame):
                    sliced = data[data[col] == code]
                elif isinstance(data, dict):
                    sliced = data[cd][data[cd][col] == code]
                temp[code] = sliced

            return temp

        return grp

    def resample(self, df: pd.DataFrame):
        df_sum_resampled = self.resample_by_agg(df=df, agg='sum')
        df_avg_resampled = self.resample_by_agg(df=df, agg='avg')

        # Concatenate aggregation
        df_resampled = pd.concat([df_sum_resampled, df_avg_resampled], axis=1)

        # Check and add dates when sales does not exist
        missed_rate = 0
        if len(df_resampled.index) != len(self.date_range):
            # missed_rate = self.check_missing_data(df=df_resampled)
            df_resampled = self.fill_missing_date(df=df_resampled)

        if self.exec_cfg['rm_outlier_yn']:
            df_resampled = self.remove_outlier(df=df_resampled, feat=self.common['target_col'])

        # Add data level
        df_resampled = self.add_data_level(org=df, resampled=df_resampled)

        return df_resampled

    def check_missiing_value(self,  df: pd.DataFrame):
        df_sum_resampled = self.resample_by_agg(df=df, agg='sum')
        df_avg_resampled = self.resample_by_agg(df=df, agg='avg')

        # Concatenate aggregation
        df_resampled = pd.concat([df_sum_resampled, df_avg_resampled], axis=1)

        # Check and add dates when sales does not exist
        missed_rate = 0
        if len(df_resampled.index) != len(self.date_range):
            missed_rate = self.check_missing_data(df=df_resampled)

        return missed_rate

    def check_missing_data(self, df):
        tot_len = len(self.date_range)
        missed = tot_len - len(df.index)
        exist = tot_len - missed
        missed_rate = 100 - round((missed / tot_len) * 100, 1)

        return exist, missed_rate

    def resample_by_agg(self, df, agg: str):
        resampled = pd.DataFrame()
        col_agg = set(df.columns).intersection(set(self.col_agg_map[agg]))
        if len(col_agg) > 0:
            resampled = df[col_agg]
            if agg == 'sum':
                resampled = resampled.resample(rule=self.resample_rule).sum()  # resampling
            elif agg == 'avg':
                resampled = resampled.resample(rule=self.resample_rule).mean()
            resampled = resampled.fillna(value=0)  # fill NaN

        return resampled

    def fill_missing_date(self, df):
        idx_add = list(set(self.date_range) - set(df.index))
        data_add = np.zeros((len(idx_add), df.shape[1]))
        df_add = pd.DataFrame(data_add, index=idx_add, columns=df.columns)
        df = df.append(df_add)
        df = df.sort_index()

        return df

    def add_data_level(self, org, resampled):
        cols = self.hrchy['apply'][:self.hrchy_level + 1]
        data_level = org[cols].iloc[0].to_dict()
        data_lvl = pd.DataFrame(data_level, index=resampled.index)
        df_resampled = pd.concat([resampled, data_lvl], axis=1)

        return df_resampled

    def impute_data(self, df: pd.DataFrame, feat: str):
        feature = deepcopy(df[feat])
        if self.imputer == 'knn':
            feature = np.where(feature.values == 0, np.nan, feature.values)
            feature = feature.reshape(-1, 1)
            imputer = KNNImputer(n_neighbors=3)
            feature = imputer.fit_transform(feature)
            feature = feature.ravel()

        elif self.imputer == 'before':
            for i in range(1, len(feature)):
                if feature[i] == 0:
                    feature[i] = feature[i-1]

        elif self.imputer == 'avg':
            for i in range(1, len(feature)-1):
                if feature[i] == 0:
                    feature[i] = (feature[i-1] + feature[i+1]) / 2

        df[feat] = feature

        return df

    def remove_outlier(self, df: pd.DataFrame, feat: str):
        feature = deepcopy(df[feat])
        lower, upper = 0, 0

        if self.outlier_method == 'std':
            feature = feature.values
            mean = np.mean(feature)
            std = np.std(feature)
            cut_off = std * self.sigma   # 99.7%
            lower = mean - cut_off
            upper = mean + cut_off

        elif self.outlier_method == 'quantile':
            lower = feature.quantile(self.quantile_range)
            upper = feature.quantile(1 - self.quantile_range)

        # feature = np.where(feature < 0, 0, feature)
        feature = np.where(feature < lower, lower, feature)    # Todo:
        feature = np.where(feature > upper, upper, feature)

        df[feat] = feature

        return df

    @staticmethod
    def make_seq_to_cust_map(df: pd.DataFrame):
        seq_to_cust = df[['seq', 'cust_cd']].set_index('seq').to_dict('index')

        return seq_to_cust

    # Temp function
    @staticmethod
    def make_miss_df(data):
        results = []
        hist = []
        for key_lvl1, val_lvl1 in data.items():
            for key_lvl2, val_lvl2 in val_lvl1.items():
                for key_lvl3, val_lvl3 in val_lvl2.items():
                    for key_lvl4, val_lvl4 in val_lvl3.items():
                        for key_lvl5, val_lvl5 in val_lvl4.items():
                            for key_lvl6, val_lvl6 in val_lvl5.items():
                                results.append([key_lvl1, key_lvl2, key_lvl3, key_lvl4, key_lvl5, key_lvl6,
                                                val_lvl6[0], val_lvl6[1]])
                                hist.append([key_lvl6, val_lvl6[0]])

        miss_df = pd.DataFrame(results, columns=['sp1', 'biz', 'line', 'brand', 'item', 'sku', 'cnt', 'rate'])
        miss_df.to_csv('missed_rate.csv', index=False, encoding='CP949')

        # Make histogram
        hist_df = pd.DataFrame(hist, columns=['sku', 'cnt'])
        ax = hist_df['cnt'].hist(bins=50)
        fig = ax.get_figure()
        fig.savefig('cnt_hist.png')

    # def add_noise_feat(self, df: pd.DataFrame) -> pd.DataFrame:
    #     vals = df[self.target_col].values * 0.05
    #     vals = vals.astype(int)
    #     vals = np.where(vals == 0, 1, vals)
    #     vals = np.where(vals < 0, vals * -1, vals)
    #     noise = np.random.randint(-vals, vals)
    #     df['exo'] = df[self.target_col].values + noise
    #
    #     return df