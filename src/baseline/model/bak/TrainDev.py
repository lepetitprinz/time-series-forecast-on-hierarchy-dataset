import common.util as util
import common.config as config
from dao.DataIO import DataIO
from common.SqlConfig import SqlConfig
from baseline.model.Algorithm import Algorithm

import os
import ast
import warnings
import numpy as np
import pandas as pd
from typing import List, Tuple, Sequence
from itertools import product
from collections import defaultdict
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings('ignore')


class TrainDev(object):
    estimators = {
        'ar': Algorithm.ar,
        'arima': Algorithm.arima,
        'hw': Algorithm.hw,
        'var': Algorithm.var,
        'varmax': Algorithm.varmax,
        'sarima': Algorithm.sarimax
    }

    def __init__(self, division: str, data_vrsn_cd: str, common: dict, hrchy: dict,
                 data_cfg: dict, exec_cfg: dict, mst_info: dict, exg_list: list, path_root: str):
        """
        :param division: Division (SELL-IN/SELl-OUT)
        :param data_vrsn_cd: Data version code
        :param common: Common information
        :param hrchy: Hierarchy information
        :param data_cfg: Data configuration
        :param exec_cfg: Execution configuration
        :param mst_info: Several master information
        :param exg_list: Exogenous variable list
        """
        # Class Configuration
        self.io = DataIO()
        self.sql_conf = SqlConfig()

        # Data Configuration
        self.path_root = path_root
        self.common = common    # Common information
        self.data_cfg = data_cfg    # Data configuration
        self.exec_cfg = exec_cfg    # Execute configuration
        self.division = division    # SELL-IN / SELL-OUT
        self.data_vrsn_cd = data_vrsn_cd    # Data version code
        self.target_col = common['target_col']    # Target column

        # self.exo_col_list = exg_list + ['discount']    # Exogenous features
        # self.exo_col_list = exg_list + ['discount', 'num_work_day']    # Todo : Test columns
        self.exo_col_list = exg_list + common['exg_fixed'].split(',')
        self.cust_grp = mst_info['cust_grp']    # Customer group master
        self.item_mst = mst_info['item_mst']    # Item master

        # Data Configuration
        self.cnt = 0    # Data level count
        self.hrchy = hrchy    # Hierarchy information
        self.err_val = float(10 ** 5 - 1)    # set error values or clip outlier values
        self.decimal_point = int(common['decimal_point'])    # Float type decimal point

        # Algorithm Configuration
        self.model_info = mst_info['model_mst']    # Algorithm master
        self.model_candidates = list(self.model_info.keys())    # Model candidates list

        # Hyper-parameter Configuration
        self.hyper_param_apply_option = 'each'    # each / best
        # self.hyper_param_apply_option = common['hyper_param_apply_option']    # Grid search option (best / each)
        self.hyper_parameter = {}    # Hyper-parameter master
        self.grid_search_space_dict = {}
        self.grid_search_space = util.conv_json_to_dict(
            path=os.path.join(self.path_root, 'config', 'grid_search_space_fcst.json')
        )
        self.grid_search_best_param_cnt = defaultdict(lambda: defaultdict(int))
        self.model_param_by_data_lvl_map = {}

        # Training Configuration
        self.n_test = 4
        self.fixed_n_test = 4
        self.validation_method = 'train_test'    # Train-test / Walk-forward

        # After processing configuration
        self.fill_na_chk_list = ['cust_grp_nm', 'item_attr03_nm', 'item_attr04_nm', 'item_nm']
        self.rm_special_char_list = ['item_attr03_nm', 'item_attr04_nm', 'item_nm']

        # Initialize
        self._init(mst_info=mst_info)

    def _init(self, mst_info: dict):
        if not self.exec_cfg['grid_search_yn']:
            self.set_hyper_parameter(mst_info=mst_info)

    def set_hyper_parameter(self, mst_info: dict):
        self.hyper_parameter['best'] = mst_info['param_grid']
        if self.hyper_param_apply_option == 'each':
            file_path = os.path.join(
                self.path_root, 'parameter', 'data_lvl_model_param_' + self.division + '_' +
                self.hrchy['key'][:-1] + '_' + str(self.n_test) + '.json'
            )
            self.hyper_parameter['each'] = self.io.load_object(file_path=file_path, data_type='json')

    def train(self, df) -> dict:
        #
        if self.exec_cfg['grid_search_yn']:
            self.set_param_grid_map()

        # # Evaluate each algorithm
        # scores = util.hrchy_recursion(
        #     hrchy_lvl=self.hrchy['lvl']['total'] - 1,
        #     fn=self.train_model,
        #     df=df
        # )

        # Evaluate each algorithm
        scores = util.hrchy_recursion_add_key(
            hrchy_lvl=self.hrchy['lvl']['total'] - 1,
            fn=self.train_model,
            df=df
        )

        return scores

    def train_model(self, hrchy, df) -> List[List[np.array]]:
        # Show prediction progress
        self.show_progress()

        # Set features by models (univ/multi)
        feature_by_variable = self.select_feature_by_variable(df=df)

        models = []
        for model in self.model_candidates:
            # Validation
            score, diff, params = self.validation(
                data=feature_by_variable[self.model_info[model]['variate']],
                model=model,
                hrchy=hrchy
            )
            models.append([model, score, diff, params])

        if self.exec_cfg['voting_yn']:
            score = self.voting(models=models)
            models.append(['voting', score, [], {}])

        models = sorted(models, key=lambda x: x[1])

        return models

    def show_progress(self) -> None:
        # Show prediction progress
        self.cnt += 1
        if (self.cnt % 1000 == 0) or (self.cnt == self.hrchy['cnt']):
            print(f"Progress: ({self.cnt} / {self.hrchy['cnt']})")

    def voting(self, models: list) -> float:
        score = self.err_val
        try:
            score = np.sqrt(np.mean((np.array([score[2] for score in models]).sum(axis=0) / len(models))**2, axis=0))
        except ValueError:
            pass

        return round(score, self.decimal_point)

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
    def validation(self, data, model: str, hrchy: list) -> Tuple[float, Sequence, dict]:
        # Train / Test Split method
        if self.validation_method == 'train_test':
            score = self.train_test_validation(data=data, model=model, hrchy=hrchy)

        # Walk-forward method
        elif self.validation_method == 'walk_forward':
            score = self.walk_fwd_validation(data=data, model=model)

        else:
            raise ValueError

        return score

    def get_hyper_parameter(self, hrchy: list):
        hyper_parameter = {}
        if self.hyper_param_apply_option == 'best':
            hyper_parameter = self.hyper_parameter['best']
        elif self.hyper_param_apply_option == 'each':
            hyper_parameter = self.hyper_parameter['each'].get(
                '_'.join(hrchy),
                self.hyper_parameter['best']
            )

        return hyper_parameter

    def train_test_validation(self, model: str, data, hrchy: list) -> Tuple[float, Sequence, dict]:
        # Set test length
        n_test = self.n_test
        # n_test = ast.literal_eval(self.model_info[model]['label_width'])

        # Split train & test dataset
        data_train, data_test = self.split_train_test(data=data, model=model, n_test=n_test)

        hyper_parameter = {}
        if not self.exec_cfg['grid_search_yn']:
            hyper_parameter = self.get_hyper_parameter(hrchy=hrchy)

        # Data Scaling
        if self.exec_cfg['scaling_yn']:
            data_train, data_test = self.scaling(
                train=data_train,
                test=data_test
            )

        best_params = {}
        if self.exec_cfg['grid_search_yn']:
            # Grid Search
            err, diff, best_params = self.grid_search(
                model=model,
                train=data_train,
                test=data_test,
                n_test=n_test
            )

        else:
            # Evaluation
            err, diff = self.evaluation(
                model=model,
                params=hyper_parameter[model],
                train=data_train,
                test=data_test,
                n_test=n_test
            )

        return err, diff, best_params

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

    # Calculate accuracy
    def calc_accuracy(self, test, pred) -> float:
        pred = np.where(pred < 0, 0, pred)    # change minus values to zero
        arr_acc = np.array([test, pred]).T
        arr_acc_marked = arr_acc[arr_acc[:, 0] != 0]

        if len(arr_acc_marked) != 0:
            acc = np.average(arr_acc_marked[:, 1] / arr_acc_marked[:, 0])
            acc = round(acc, self.decimal_point)
        else:
            # acc = np.nan
            acc = self.err_val

        return acc

    # evaluation
    def evaluation(self, model, params, train, test, n_test) -> Tuple[float, Sequence]:
        # get the length of train dataset
        if self.model_info[model]['variate'] == 'univ':
            len_train = len(train)
            len_test = len(test)
        else:
            len_train = len(train['endog'])
            len_test = len(test['endog'])

        err = self.err_val
        diff = [self.err_val] * len_test
        if len_train >= self.fixed_n_test:   # Evaluate if data length is bigger than minimum threshold
            try:
                yhat = self.estimators[model](
                    history=train,    # Train dataset
                    cfg=params,       # Hyper-parameter
                    pred_step=n_test  # Prediction range
                )
                if yhat is not None:
                    if len_test < n_test:
                        yhat = yhat[:len_test]
                    if self.model_info[model]['variate'] == 'univ':
                        err = round(mean_squared_error(test, yhat, squared=False), self.decimal_point)
                        diff = test - yhat
                        diff = diff.values
                        # acc = round(self.calc_accuracy(test=test, pred=yhat), self.decimal_point)

                    elif self.model_info[model]['variate'] == 'multi':
                        err = round(mean_squared_error(test['endog'], yhat, squared=False), self.decimal_point)
                        diff = test['endog'] - yhat
                        # acc = round(self.calc_accuracy(test=test['endog'], pred=yhat), self.decimal_point)

                    # Clip error values
                    if err > self.err_val:
                        err = self.err_val

            except ValueError:
                pass

        return err, diff

    # Grid search
    def grid_search(self, model, train, test, n_test) -> Tuple[float, Sequence, dict]:
        # Get hyper-parameter grid for current algorithm
        param_grid_list = self.grid_search_space_dict[model]

        err_list = []
        for params in param_grid_list:
            err, diff = self.evaluation(
                model=model,
                params=params,
                train=train,
                test=test,
                n_test=n_test
            )
            err_list.append((err, diff, params))

        err_list = sorted(err_list, key=lambda x: x[0])    # Sort result based on error score
        best_result = err_list[0]    # Get the best result of grid search

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
        n_test = ast.literal_eval(self.model_info[model]['label_width'])    # Change data type
        predictions = []
        for train, test in dataset:
            yhat = self.estimators[model](history=train, cfg=self.hyper_parameter[model], pred_step=n_test)
            yhat = np.nan_to_num(yhat)
            err = mean_squared_error(test, yhat, squared=False)
            predictions.append(err)

        # estimate prediction error
        rmse = np.mean(predictions)

        return rmse

    @staticmethod
    def scaling(train, test) -> tuple:
        # Split train and test dataset
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

    def set_param_grid_map(self) -> None:
        param_grid_map = {}
        for model, param_grid in self.grid_search_space.items():
            params = list(param_grid.keys())
            values = param_grid.values()
            values_combine_list = list(product(*values))

            values_combine_map_list = []
            for values_combine in values_combine_list:
                values_combine_map_list.append(dict(zip(params, values_combine)))

            param_grid_map[model] = values_combine_map_list

        self.grid_search_space_dict = param_grid_map

    def get_param_list(self, model) -> List[dict]:
        param_grids = self.grid_search_space[model]    # Hyper-parameter list
        params = list(param_grids.keys())    # Hyper-parameter options
        values = param_grids.values()    # Hyper-parameter values
        values_combine_list = list(product(*values))

        values_combine_map_list = []
        for values_combine in values_combine_list:
            values_combine_map_list.append(dict(zip(params, values_combine)))

        return values_combine_map_list

    def save_params(self, scores) -> None:
        if self.hyper_param_apply_option == 'best':
            self.save_most_cnt_params(scores=scores)

        elif self.hyper_param_apply_option == 'each':
            self.save_each_params(scores=scores)

    def save_each_params(self, scores) -> None:
        # Count best params for each data level
        util.hrchy_recursion_with_key(
            hrchy_lvl=self.hrchy['lvl']['total'] - 1,
            fn=self.make_model_param_map,
            df=scores
        )
        file_path = os.path.join(
            self.path_root, 'parameter', 'data_lvl_model_param_' + self.division + '_' +
                                         self.hrchy['key'][:-1] + '_' + str(self.n_test) + '.json'
        )
        self.io.save_object(data=self.model_param_by_data_lvl_map, data_type='json', file_path=file_path)

    # Make the mapping dictionary
    def make_model_param_map(self, hrchy, data):
        model_param_map = {}
        for eval_result in data:
            if eval_result[0] != 'voting':
                model, _, _, params = eval_result
                model_param_map[model] = params

        self.model_param_by_data_lvl_map['_'.join(hrchy)] = model_param_map

    # Save the most counted hyper-parameter set
    def save_most_cnt_params(self, scores) -> None:
        # Count best params for each data level
        util.hrchy_recursion(
            hrchy_lvl=self.hrchy['lvl']['total'] - 1,
            fn=self.count_best_params,
            df=scores
        )

        for model, count in self.grid_search_best_param_cnt.items():
            params = [(val, key) for key, val in count.items()]
            params = sorted(params, key=lambda x: x[0], reverse=True)
            best_params = eval(params[0][1])
            best_params, params_info_list = self.make_best_params_data(model=model, params=best_params)

            for params_info in params_info_list:
                self.io.delete_from_db(sql=self.sql_conf.del_hyper_params(**params_info))
            self.io.insert_to_db(df=best_params, tb_name='M4S_I103011')

    # Count best hyper-parameters
    def count_best_params(self, data) -> None:
        for algorithm in data:
            if algorithm[0] != 'voting':
                model, score, diff, params = algorithm
                self.grid_search_best_param_cnt[model][str(params)] += 1

    def make_score_result(self, data: dict, hrchy_key: str, fn) -> Tuple[pd.DataFrame, dict]:
        hrchy_tot_lvl = self.hrchy['lvl']['cust'] + self.hrchy['lvl']['item'] - 1
        result = util.hrchy_recursion_extend_key(hrchy_lvl=hrchy_tot_lvl, fn=fn, df=data)

        # Convert to dataframe
        result = pd.DataFrame(result)
        cols = self.hrchy['apply'] + ['stat_cd', 'rmse', 'diff']
        result.columns = cols
        result = result.drop(columns=['diff'])

        # Add information
        result['project_cd'] = self.common['project_cd']    # Project code
        result['division_cd'] = self.division
        result['data_vrsn_cd'] = self.data_vrsn_cd
        result['create_user_cd'] = 'SYSTEM'

        if hrchy_key[:2] == 'C1':    # if hierarchy contains SP1 (Customer group)
            if hrchy_key[3:5] == 'P5':    # if hierarchy contains SKU code
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
        # 1.Item code & name
        if self.hrchy['lvl']['item'] > 0:
            result = pd.merge(
                result,
                self.item_mst[config.COL_ITEM[: 2 * self.hrchy['lvl']['item']]].drop_duplicates(),
                on=self.hrchy['list']['item'][:self.hrchy['lvl']['item']],
                how='left', suffixes=('', '_DROP')
            ).filter(regex='^(?!.*_DROP)')

        # 2.SP1 code & name
        if self.hrchy['lvl']['cust'] > 0:
            result = pd.merge(
                result,
                self.cust_grp[config.COL_CUST[: 2 * self.hrchy['lvl']['cust']]].drop_duplicates(),
                on=self.hrchy['list']['cust'][:self.hrchy['lvl']['cust']],
                how='left', suffixes=('', '_DROP')
            ).filter(regex='^(?!.*_DROP)')

        # Fill null values
        result = util.fill_na(data=result, chk_list=self.fill_na_chk_list)

        # Rename columns
        result = result.rename(columns=config.HRCHY_CD_TO_DB_CD_MAP)
        result = result.rename(columns=config.HRCHY_SKU_TO_DB_SKU_MAP)

        # Remove Special Character
        for col in self.rm_special_char_list:
            if col in list(result.columns):
                result = util.remove_special_character(data=result, feature=col)

        # set score information used to delete previous results
        score_info = {
            'project_cd': self.common['project_cd'],
            'data_vrsn_cd': self.data_vrsn_cd,
            'division_cd': self.division,
            'fkey': hrchy_key[:-1]
        }

        return result, score_info

    @staticmethod
    # Save all of scores to dataframe
    def conv_score_to_df(hrchy: list, data) -> List[list]:
        result = []
        for algorithm, err, accuracy, _ in data:
            # result.append(hrchy + [algorithm.upper(), score])
            result.append(hrchy + [algorithm.upper(), err, accuracy])

        return result

    @staticmethod
    # Save best scores to dataframe
    def conv_best_score_df(hrchy: list, data) -> list:
        result = []
        for algorithm, err, accuracy, _ in data:
            # result.append(hrchy + [algorithm.upper(), score])
            result.append(hrchy + [algorithm.upper(), err, accuracy])

        result = sorted(result, key=lambda x: x[2])

        return [result[0]]

    # Make the sliding window data
    def window_generator(self, df, model: str) -> List[Tuple]:
        data_length = len(df)
        input_width = int(self.model_info[model]['input_width'])
        label_width = int(self.model_info[model]['label_width'])
        data_input = None
        data_target = None
        dataset = []
        for i in range(data_length - input_width - label_width + 1):
            # Univariate variable
            if self.model_info[model]['variate'] == 'univ':
                data_input = df.iloc[i: i + input_width]
                data_target = df.iloc[i + input_width: i + input_width + label_width]
            # Multivariate variable
            elif self.model_info[model]['variate'] == 'multi':
                data_input = df.iloc[i: i + input_width, :]
                data_target = df.iloc[i + input_width: i + input_width + label_width, :]

            dataset.append((data_input, data_target))

        return dataset