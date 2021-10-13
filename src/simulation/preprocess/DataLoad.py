import common.util as util
import common.config as config
from common.SqlConfig import SqlConfig


class DataLoad(object):
    def __init__(self, division: str, hrchy_lvl: int, lag: str,
                 save_obj_yn: bool, load_obj_yn: bool):
        # initiate class
        self.sql_conf = SqlConfig()

        # data option
        self.common = {}
        self.date = {}
        self.data_version = ''
        self.division = division
        self.hrchy_lvl = hrchy_lvl
        self.lag = lag

        # Dataset
        self.sales = None
        self.exg = {}
        self.algorithms = {}
        self.parameters = {}

        # model configuration
        self.target_col = ''
        self.save_obj_yn = save_obj_yn
        self.load_obj_yn = load_obj_yn

    def init(self, io):
        self.common = io.get_dict_from_db(sql=SqlConfig.sql_comm_master(), key='OPTION_CD', val='OPTION_VAL')
        self.date = {'date_from': self.common['rst_start_day'], 'date_to': self.common['rst_end_day']}
        # self.data_version = str(self.date['date_from']) + '-' + str(self.date['date_to'])
        self.data_version = '20210101-20210530'
        self.target_col = self.common['target_col']

    def load(self, io):
        if not self.load_obj_yn:
            # Sales Dataset
            if self.division == 'sell_in':
                self.sales = io.get_df_from_db(sql=self.sql_conf.sql_sell_in(**self.date))
            elif self.division == 'sell_out':
                self.sales = io.get_df_from_db(sql=self.sql_conf.sql_sell_out(**self.date))

            if self.save_obj_yn:
                file_path = util.make_path_sim(module='simulation', division=self.division, step='load',
                                               extension='csv')
                io.save_object(data=self.sales, file_path=file_path, data_type='csv')

        else:
            file_path = util.make_path_sim(
                module='simulation', division=self.division, step='load', extension='csv')
            self.sales = io.load_object(file_path=file_path, data_type='csv')

        # Exogenous dataset
        exg_all = io.get_df_from_db(sql=SqlConfig.sql_exg_data(partial_yn='N'))
        exg_partial = io.get_df_from_db(sql=SqlConfig.sql_exg_data(partial_yn='Y'))
        exg_list = list(idx.lower() for idx in exg_all['idx_cd'].unique())
        self.exg = {'all': exg_all, 'partial': exg_partial}

        # Algorithm
        algorithms = io.get_df_from_db(sql=SqlConfig.sql_algorithm(**{'division': 'SIM'}))
        self.algorithms = algorithms['model'].to_list()

        # Hyper parameters
        param_grids = config.PARAM_GRIDS_SIM
        param_best = io.get_df_from_db(sql=SqlConfig.sql_best_hyper_param_grid())

        # convert string type int to int type
        option_val = [eval(val) if val.isnumeric() else val for val in param_best['option_val']]
        param_best['option_val'] = option_val

        # convert upper case to lower case
        param_best['stat_cd'] = param_best['stat_cd'].apply(lambda x: x.lower())
        param_best['option_cd'] = param_best['option_cd'].apply(lambda x: x.lower())

        # map key-value pair
        param_best = util.make_lvl_key_val_map(df=param_best, lvl='stat_cd', key='option_cd', val='option_val')
        self.parameters = {'param_grids': param_grids, 'param_best': param_best}