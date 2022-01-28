import common.util as util
import common.config as config
from dao.DataIO import DataIO
from common.SqlConfig import SqlConfig
from baseline.model.Algorithm import Algorithm
# from baseline.model.ModelDL import Models

import ast
import warnings
import numpy as np
import pandas as pd
from typing import List, Tuple
from itertools import product
from collections import defaultdict
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings('ignore')


class Train(object):
    estimators = {
        'ar': Algorithm.ar,
        'arima': Algorithm.arima,
        'hw': Algorithm.hw,
        'var': Algorithm.var,
        'varmax': Algorithm.varmax,
        'sarima': Algorithm.sarimax
    }

    def __init__(self, mst_info: dict, common: dict, division: str, data_vrsn_cd: str,
                 hrchy: dict, exg_list: list, data_cfg: dict, exec_cfg: dict):
        # Class Configuration
        self.io = DataIO()
        self.sql_conf = SqlConfig()

        # Data Configuration
        self.data_cfg = data_cfg
        self.exec_cfg = exec_cfg
        self.data_vrsn_cd = data_vrsn_cd
        self.common = common
        self.division = division    # SELL-IN / SELL-OUT
        self.target_col = common['target_col']    # Target column

        self.exo_col_list = exg_list + ['discount']    # Exogenous features
        self.cust_grp = mst_info['cust_grp']
        self.item_mst = mst_info['item_mst']

        # Data Level Configuration
        self.cnt = 0
        self.hrchy = hrchy

        # Algorithm Configuration
        self.model_info = mst_info['model_mst']     # Algorithm master
        self.param_grid = mst_info['param_grid']    # Hyper-parameter master
        self.param_grid_list = config.PARAM_GRIDS_FCST    # Todo: Correct later
        self.model_candidates = list(self.model_info.keys())

        # Training Configuration
        self.fixed_n_test = 4
        self.err_val = float(10 ** 5 - 1)
        self.validation_method = 'train_test'
        self.grid_search_yn: bool = exec_cfg['grid_search_yn']    # Execute grid search or not
        self.best_params_cnt = defaultdict(lambda: defaultdict(int))

        # After processing Configuration
        self.fill_na_chk_list = ['cust_grp_nm', 'item_attr03_nm', 'item_attr04_nm', 'item_nm']
        self.rm_special_char_list = ['item_attr03_nm', 'item_attr04_nm', 'item_nm']

    def train(self, df) -> dict:
        # Evaluate each algorithm
        scores = util.hrchy_recursion(
            hrchy_lvl=self.hrchy['lvl']['total'] - 1,
            fn=self.train_model,
            df=df
        )

        return scores

    def train_model(self, df) -> List[List[np.array]]:
        # Print training progress
        self.cnt += 1
        if (self.cnt % 1000 == 0) or (self.cnt == self.hrchy['cnt']):
            print(f"Progress: ({self.cnt} / {self.hrchy['cnt']})")

        # Set features by models (univ/multi)
        feature_by_variable = self.select_feature_by_variable(df=df)

        models = []
        for model in self.model_candidates:
            # Validation
            score = self.validation(
                data=feature_by_variable[self.model_info[model]['variate']],
                model=model)

            models.append([model, score[0], score[1], score[2]])
        models = sorted(models, key=lambda x: x[1])

        return models

    # Split univariate / multivariate features
    def select_feature_by_variable(self, df: pd.DataFrame) -> dict:
        feature_by_variable = None
        try:
            feature_by_variable = {'univ': df[self.target_col],    # Univariate columns
                                   'multi': df[self.exo_col_list + [self.target_col]]}    # Multivariate columns
        except ValueError:
            print("Data dose not have some columns")

        return feature_by_variable

    # Validation
    def validation(self, data, model: str) -> Tuple[float, float, dict]:
        # Train / Test Split method
        if self.validation_method == 'train_test':
            score = self.train_test_validation(data=data, model=model)

        # Walk-forward method
        elif self.validation_method == 'walk_forward':
            score = self.walk_fwd_validation(data=data, model=model)

        else:
            raise ValueError

        return score

    def train_test_validation(self, model: str, data) -> Tuple[float, float, dict]:
        # Set test length
        n_test = ast.literal_eval(self.model_info[model]['label_width'])

        # Split train & test dataset
        data_train, data_test = self.split_train_test(data=data, model=model, n_test=n_test)

        # Data Scaling
        if self.exec_cfg['scaling_yn']:
            data_train, data_test = self.scaling(
                train=data_train,
                test=data_test
            )

        # Grid Search
        acc = 0
        best_params = {}
        if self.grid_search_yn:
            err, best_params = self.grid_search(
                model=model,
                train=data_train,
                test=data_test,
                n_test=n_test
            )

        else:
            err, acc = self.evaluation(
                model=model,
                params=self.param_grid[model],
                train=data_train,
                test=data_test,
                n_test=n_test
            )

        return err, acc, best_params

    def split_train_test(self, data: pd.DataFrame, model: str, n_test: int) -> Tuple[dict, dict]:
        data_length = len(data)

        data_train, data_test = None, None
        if self.model_info[model]['variate'] == 'univ':
            if data_length - n_test >= n_test:    # if training period bigger than prediction
                data_train = data.iloc[: data_length - n_test]
                data_test = data.iloc[data_length - n_test:]

            elif data_length > self.fixed_n_test:    # if data period bigger than fixed period
                data_train = data.iloc[: data_length - self.fixed_n_test]
                data_test = data.iloc[data_length - self.fixed_n_test:]

            else:
                data_train = data.iloc[: data_length - 1]
                data_test = data.iloc[data_length - 1:]

        elif self.model_info[model]['variate'] == 'multi':
            if data_length - n_test >= n_test:    # if training period bigger than prediction
                data_train = data.iloc[: data_length - n_test, :]
                data_test = data.iloc[data_length - n_test:, :]

            elif data_length > self.fixed_n_test:    # if data period bigger than fixed period
                data_train = data.iloc[: data_length - self.fixed_n_test, :]
                data_test = data.iloc[data_length - self.fixed_n_test:, :]

            else:
                data_train = data.iloc[: data_length - 1, :]
                data_test = data.iloc[data_length - 1:, :]

            x_train = data_train[self.exo_col_list].values
            x_test = data_test[self.exo_col_list].values

            data_train = {
                'endog': data_train[self.target_col].values.ravel(),    # Target variable
                'exog': x_train    # Input variable
            }
            data_test = {
                'endog': data_test[self.target_col].values,    # Target variable
                'exog': x_test    # Input variable
            }

        return data_train, data_test

    @staticmethod
    # Calculate accuracy
    def calc_accuracy(test, pred) -> float:
        pred = np.where(pred < 0, 0, pred)
        arr_acc = np.array([test, pred]).T
        arr_acc_marked = arr_acc[arr_acc[:, 0] != 0]

        if len(arr_acc_marked) != 0:
            acc = np.average(arr_acc_marked[:, 1] / arr_acc_marked[:, 0])
            acc = round(acc, 2)
        else:
            # acc = np.nan
            acc = 10**5 - 1

        return acc

    def evaluation(self, model, params, train, test, n_test) -> Tuple[float, float]:
        # evaluation
        acc = 0
        if self.model_info[model]['variate'] == 'univ':
            length = len(train)
        else:
            length = len(train['endog'])

        if length > self.fixed_n_test:   # Evaluate if data length is bigger than minimum threshold
            try:
                yhat = self.estimators[model](
                    history=train,
                    cfg=params,
                    pred_step=n_test
                )

                if yhat is not None:
                    err = 0
                    if self.model_info[model]['variate'] == 'univ':
                        err = round(mean_squared_error(test, yhat, squared=False), 2)
                        # acc = round(self.calc_accuracy(test=test, pred=yhat), 2)
                        acc = 0

                    elif self.model_info[model]['variate'] == 'multi':
                        err = round(mean_squared_error(test['endog'], yhat, squared=False), 2)
                        # acc = round(self.calc_accuracy(test=test['endog'], pred=yhat), 2)
                        acc = 0

                    # Exception
                    if err > self.err_val:
                        err = self.err_val    # Clip error values
                else:
                    err = self.err_val    # Not solvable problem

            except ValueError:
                err = self.err_val    # Not solvable problem
        else:
            err = self.err_val

        return err, acc

    def grid_search(self, model, train, test, n_test) -> Tuple[tuple, dict]:
        # get hyper-parameter grid for current algorithm
        param_grid_list = self.get_param_list(model=model)

        err_list = []
        for params in param_grid_list:
            err = self.evaluation(
                model=model,
                params=params,
                train=train,
                test=test,
                n_test=n_test
            )
            err_list.append((err, params))

        err_list = sorted(err_list, key=lambda x: x[0])    # Sort result based on error score
        best_result = err_list[0]    # Get best result

        return best_result

    def walk_fwd_validation(self, model: str, data) -> np.array:
        """
        :param model: Statistical model
        :param data: time series data
        :return:
        """
        # split dataset
        dataset = self.window_generator(df=data, model=model)

        # evaluation
        n_test = ast.literal_eval(self.model_info[model]['label_width'])
        predictions = []
        for train, test in dataset:
            yhat = self.estimators[model](history=train, cfg=self.param_grid[model], pred_step=n_test)
            yhat = np.nan_to_num(yhat)
            err = mean_squared_error(test, yhat, squared=False)
            predictions.append(err)

        # estimate prediction error
        rmse = np.mean(predictions)

        return rmse

    @staticmethod
    def scaling(train, test) -> tuple:
        # split train and test dataset
        x_train = train['exog']
        x_test = test['exog']

        # Apply Min-Max Scaling
        scaler = MinMaxScaler()
        x_train_scaled = scaler.fit_transform(x_train)
        x_test_scaled = scaler.transform(x_test)

        train['exog'] = x_train_scaled
        test['exog'] = x_test_scaled

        return train, test

    def make_best_params_data(self, model: str, params: dict) -> tuple:
        model = model.upper()    # Convert name to uppercase
        data, info = [], []
        for key, val in params.items():
            data.append([
                self.common['project_cd'],
                model,
                key.upper(),
                str(val)
            ])
            info.append({
                'project_cd': self.common['project_cd'],
                'stat_cd': model,
                'option_cd': key.upper()
            })
        param_df = pd.DataFrame(data, columns=['PROJECT_CD', 'STAT_CD', 'OPTION_CD', 'OPTION_VAL'])

        return param_df, info

    def get_param_list(self, model) -> List[dict]:
        param_grids = self.param_grid_list[model]
        params = list(param_grids.keys())
        values = param_grids.values()
        values_combine_list = list(product(*values))

        values_combine_map_list = []
        for values_combine in values_combine_list:
            values_combine_map_list.append(dict(zip(params, values_combine)))

        return values_combine_map_list

    def save_best_params(self, scores) -> None:
        # Count best params for each data level
        util.hrchy_recursion(
            hrchy_lvl=self.hrchy['lvl']['total'] - 1,
            fn=self.count_best_params,
            df=scores
        )

        for model, count in self.best_params_cnt.items():
            params = [(val, key) for key, val in count.items()]
            params = sorted(params, key=lambda x: x[0], reverse=True)
            best_params = eval(params[0][1])
            best_params, params_info_list = self.make_best_params_data(model=model, params=best_params)

            for params_info in params_info_list:
                self.io.delete_from_db(sql=self.sql_conf.del_hyper_params(**params_info))
            self.io.insert_to_db(df=best_params, tb_name='M4S_I103011')

    def count_best_params(self, data) -> None:
        for algorithm in data:
            model, score, accuracy, params = algorithm
            self.best_params_cnt[model][str(params)] += 1

    def make_score_result(self, data: dict, hrchy_key: str, fn) -> Tuple[pd.DataFrame, dict]:
        hrchy_tot_lvl = self.hrchy['lvl']['cust'] + self.hrchy['lvl']['item'] - 1
        result = util.hrchy_recursion_extend_key(hrchy_lvl=hrchy_tot_lvl, fn=fn, df=data)

        # Convert to dataframe
        result = pd.DataFrame(result)
        cols = self.hrchy['apply'] + ['stat_cd', 'rmse', 'accuracy']
        result.columns = cols

        # Add information
        result['project_cd'] = self.common['project_cd']
        result['division_cd'] = self.division
        result['data_vrsn_cd'] = self.data_vrsn_cd
        result['create_user_cd'] = 'SYSTEM'

        if hrchy_key[:2] == 'C1':
            if hrchy_key[3:5] == 'P5':
                result['fkey'] = hrchy_key + result['cust_grp_cd'] + '-' + result['sku_cd']
            else:
                key = self.hrchy['apply'][-1]
                result['fkey'] = hrchy_key + result['cust_grp_cd'] + '-' + result[key]
        else:
            key = self.hrchy['apply'][-1]
            result['fkey'] = hrchy_key + result[key]

        result['rmse'] = result['rmse'].fillna(0)
        # result['accuracy'] = result['accuracy'].where(pd.notnull(result['accuracy']), None)

        # Merge information
        # Item Names
        if self.hrchy['lvl']['item'] > 0:
            result = pd.merge(result,
                              self.item_mst[config.COL_ITEM[: 2 * self.hrchy['lvl']['item']]].drop_duplicates(),
                              on=self.hrchy['list']['item'][:self.hrchy['lvl']['item']],
                              how='left', suffixes=('', '_DROP')).filter(regex='^(?!.*_DROP)')

        # Customer Names
        if self.hrchy['lvl']['cust'] > 0:
            result = pd.merge(result,
                              self.cust_grp[config.COL_CUST[: 2 * self.hrchy['lvl']['cust']]].drop_duplicates(),
                              on=self.hrchy['list']['cust'][:self.hrchy['lvl']['cust']],
                              how='left', suffixes=('', '_DROP')).filter(regex='^(?!.*_DROP)')
            # result = result.fillna('-')

        # Fill na
        result = util.fill_na(data=result, chk_list=self.fill_na_chk_list)

        # Rename columns
        result = result.rename(columns=config.HRCHY_CD_TO_DB_CD_MAP)
        result = result.rename(columns=config.HRCHY_SKU_TO_DB_SKU_MAP)

        # Remove Special Character
        for col in self.rm_special_char_list:
            if col in list(result.columns):
                result = util.remove_special_character(data=result, feature=col)

        # set score_info
        score_info = {
            'project_cd': self.common['project_cd'],
            'data_vrsn_cd': self.data_vrsn_cd,
            'division_cd': self.division,
            'fkey': hrchy_key[:-1]
        }

        return result, score_info

    @staticmethod
    def score_to_df(hrchy: list, data) -> List[list]:
        result = []
        for algorithm, err, accuracy, _ in data:
            # result.append(hrchy + [algorithm.upper(), score])
            result.append(hrchy + [algorithm.upper(), err, accuracy])    # ToDo: Correct score (err, accuracy)

        return result

    @staticmethod
    def best_score_to_df(hrchy: list, data) -> list:
        result = []
        for algorithm, err, accuracy, _ in data:
            # result.append(hrchy + [algorithm.upper(), score])
            result.append(hrchy + [algorithm.upper(), err, accuracy])  # ToDo: Correct score (err, accuracy)

        result = sorted(result, key=lambda x: x[2])

        return [result[0]]

    def window_generator(self, df, model: str) -> List[Tuple]:
        data_length = len(df)
        input_width = int(self.model_info[model]['input_width'])
        label_width = int(self.model_info[model]['label_width'])
        data_input = None
        data_target = None
        dataset = []
        for i in range(data_length - input_width - label_width + 1):
            if self.model_info[model]['variate'] == 'univ':
                data_input = df.iloc[i: i + input_width]
                data_target = df.iloc[i + input_width: i + input_width + label_width]
            elif self.model_info[model]['variate'] == 'multi':
                data_input = df.iloc[i: i + input_width, :]
                data_target = df.iloc[i + input_width: i + input_width + label_width, :]

            dataset.append((data_input, data_target))

        return dataset
