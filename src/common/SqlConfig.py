
class SqlConfig(object):
    @staticmethod
    def sql_data_version():
        sql = f"""
            SELECT DATA_VRSN_CD
              FROM M4S_I110420
            """
        return sql

    @staticmethod
    def sql_comm_master():
        sql = f"""
            SELECT OPTION_CD
                 , OPTION_VAL
              FROM M4S_I001020
             WHERE MDL_CD = 'DF'
            """
        return sql

    @staticmethod
    def sql_item_view():
        sql = """
            SELECT ITEM_ATTR01_CD AS BIZ_CD
                 , ITEM_ATTR01_NM AS BIZ_NM
                 , ITEM_ATTR02_CD AS LINE_CD
                 , ITEM_ATTR02_NM AS LINE_NM
                 , ITEM_ATTR03_CD AS BRAND_CD
                 , ITEM_ATTR03_NM AS BRAND_NM
                 , ITEM_ATTR04_CD AS ITEM_CD
                 , ITEM_ATTR04_NM AS ITEM_NM
                 , ITEM_CD AS SKU_CD
                 , ITEM_NM AS SKU_NM
              FROM VIEW_I002040
             WHERE ITEM_TYPE_CD IN ('FERT', 'HAWA')
             GROUP BY ITEM_ATTR01_CD
                    , ITEM_ATTR01_NM
                    , ITEM_ATTR02_CD
                    , ITEM_ATTR02_NM
                    , ITEM_ATTR03_CD
                    , ITEM_ATTR03_NM
                    , ITEM_ATTR04_CD
                    , ITEM_ATTR04_NM
                    , ITEM_CD
                    , ITEM_NM
        """
        return sql

    @staticmethod
    def sql_cust_code():
        sql = """
            SELECT CUST_CD
                 , CUST_GRP_CD
              FROM (
                    SELECT CUST.CUST_CD
                         , CUST.CUST_GRP_CD
                         , ROW_NUMBER() over (PARTITION BY CUST_CD, GRP.CUST_GRP_CD 
                                              ORDER BY CUST_CD, GRP.CUST_GRP_CD) AS RANK
                      FROM (
                            SELECT CUST_GRP_CD
                                 , CUST_CD
                                 , CUST_NM
                              FROM M4S_I002060
                             WHERE USE_YN = 'Y'
                           ) CUST
                      LEFT OUTER JOIN (
                                       SELECT CUST_GRP_CD
                                            , CUST_GRP_NM
                                         FROM M4S_I002050
                                        WHERE USE_YN = 'Y'
                                      ) GRP
                        ON CUST.CUST_GRP_CD = GRP.CUST_GRP_CD
                   ) RSLT
             WHERE RANK = 1
        """
        return sql

    @staticmethod
    def sql_cust_info_bak():
        sql = """
            SELECT CUST.CUST_GRP_CD
                 , GRP.CUST_GRP_NM
                 , CUST.CUST_CD
                 , CUST_NM
              FROM (
                    SELECT CUST_GRP_CD
                         , CUST_CD
                         , CUST_NM
                      FROM M4S_I002060
                     WHERE USE_YN = 'Y'
                   ) CUST
              LEFT OUTER JOIN (
                               SELECT CUST_GRP_CD
                                    , CUST_GRP_NM
                                 FROM M4S_I002050
                             WHERE USE_YN = 'Y'
                              ) GRP
                ON CUST.CUST_GRP_CD = GRP.CUST_GRP_CD
        """
        return sql

    @staticmethod
    def sql_cust_grp_info():
        sql = """
              SELECT LINK_SALES_MGMT_CD AS CUST_GRP_CD
                   , LINK_SALES_MGMT_NM AS CUST_GRP_NM
                FROM M4S_I204020
               WHERE PROJECT_CD = 'ENT001'
                 AND SALES_MGMT_VRSN_ID = '202111_V0'
                 AND USE_YN = 'Y'
        """
        return sql

    @staticmethod
    def sql_calendar():
        sql = """
            SELECT YYMMDD
                 , WEEK
              FROM M4S_I002030
        """
        return sql

    # SELL-IN Table
    @staticmethod
    def sql_sell_in(**kwargs):
        sql = f""" 
                    SELECT DIVISION_CD
                         , CUST_GRP_CD
                         , BIZ_CD
                         , LINE_CD
                         , BRAND_CD
                         , ITEM_CD
                         , SALES.SKU_CD
--                          , CONVERT(CHAR, DATEADD(WEEK, 15, CONVERT(DATE, YYMMDD)), 112) AS YYMMDD 
                         , YYMMDD
                         , SEQ
                         , FROM_DC_CD
                         , UNIT_PRICE
                         , UNIT_CD
                         , DISCOUNT
                         , WEEK
                         , QTY
                         , CREATE_DATE
                      FROM (
                            SELECT PROJECT_CD
                                 , DIVISION_CD
                                 , SOLD_CUST_GRP_CD AS CUST_GRP_CD
                                 , ITEM_CD AS SKU_CD
                                 , YYMMDD
                                 , SEQ
                                 , FROM_DC_CD
                                 , UNIT_PRICE
                                 , RTRIM(UNIT_CD) AS UNIT_CD
                                 , DISCOUNT
                                 , WEEK
                                 , RST_SALES_QTY AS QTY
                                 , CREATE_DATE
                              FROM M4S_I002170
                             WHERE YYMMDD BETWEEN {kwargs['date_from']} AND {kwargs['date_to']}
                            ) SALES
                      LEFT OUTER JOIN (
                                       SELECT ITEM_CD AS SKU_CD
                                            , ITEM_ATTR01_CD AS BIZ_CD
                                            , ITEM_ATTR02_CD AS LINE_CD
                                            , ITEM_ATTR03_CD AS BRAND_CD
                                            , ITEM_ATTR04_CD AS ITEM_CD
                                         FROM VIEW_I002040
                                        WHERE ITEM_TYPE_CD IN ('HAWA', 'FERT')
                                      ) ITEM
                        ON SALES.SKU_CD = ITEM.SKU_CD
               """
        return sql

    # SELL-OUT Table
    @staticmethod
    def sql_sell_out(**kwargs):
        sql = f""" 
           SELECT DIVISION_CD
                , CUST_CD
                , BIZ_CD
                , LINE_CD
                , BRAND_CD
                , ITEM_CD
                , SALES.SKU_CD AS SKU_CD 
                , YYMMDD
                , SEQ
                , DISCOUNT
                , WEEK
                , QTY
                , CREATE_DATE
             FROM (
                   SELECT PROJECT_CD
                        , DIVISION_CD
                        , SOLD_CUST_GRP_CD AS CUST_CD
                        , ITEM_CD AS SKU_CD
                        , YYMMDD
                        , SEQ
                        , DISCOUNT
                        , WEEK
                        , RST_SALES_QTY AS QTY
                        , CREATE_DATE
                     FROM M4S_I002173
                   -- WHERE YYMMDD BETWEEN {kwargs['date_from']} AND {kwargs['date_to']} # Todo: Exception
                   ) SALES
             LEFT OUTER JOIN (
                              SELECT ITEM_CD AS SKU_CD
                                   , ITEM_ATTR01_CD AS BIZ_CD
                                   , ITEM_ATTR02_CD AS LINE_CD
                                   , ITEM_ATTR03_CD AS BRAND_CD
                                   , ITEM_ATTR04_CD AS ITEM_CD
                                FROM VIEW_I002040
                               WHERE ITEM_TYPE_CD IN ('HAWA', 'FERT')
                             ) ITEM
               ON SALES.SKU_CD = ITEM.SKU_CD
               """
        return sql

    @staticmethod
    def sql_unit_map():
        sql = """
            SELECT BOX.ITEM_CD AS SKU_CD
                 , CONVERT(INT, BOX.FAC_PRICE / BOL.FAC_PRICE) AS BOX_BOL
                 , CONVERT(INT, BOX.FAC_PRICE / EA.FAC_PRICE) AS BOX_EA
              FROM (
                    SELECT PROJECT_CD
                         , ITEM_CD
                         , PRICE_START_YYMMDD
                         , FAC_PRICE
                    FROM M4S_I002041
                   WHERE PRICE_QTY_UNIT_CD = 'BOX'
                     AND FAC_PRICE <> 0
                    ) BOX
              LEFT OUTER JOIN (
                               SELECT PROJECT_CD
                                    , ITEM_CD
                                    , PRICE_START_YYMMDD
                                    , FAC_PRICE
                                 FROM M4S_I002041
                                WHERE PRICE_QTY_UNIT_CD = 'BOL'
                                  AND FAC_PRICE <> 0
                              ) BOL
                ON BOX.PROJECT_CD = BOL.PROJECT_CD
               AND BOX.ITEM_CD = BOL.ITEM_CD
               AND BOX.PRICE_START_YYMMDD = BOL.PRICE_START_YYMMDD
              LEFT OUTER JOIN (
                               SELECT PROJECT_CD
                                    , ITEM_CD
                                    , PRICE_START_YYMMDD
                                    , FAC_PRICE
                                 FROM M4S_I002041
                                WHERE PRICE_QTY_UNIT_CD = 'EA'
                                  AND FAC_PRICE <> 0
                               ) EA
                ON BOX.PROJECT_CD = EA.PROJECT_CD
               AND BOX.ITEM_CD = EA.ITEM_CD
               AND BOX.PRICE_START_YYMMDD = EA.PRICE_START_YYMMDD
            """
        return sql

    @staticmethod
    def sql_algorithm(**kwargs):
        sql = f"""
            SELECT LOWER(STAT_CD) AS MODEL
                 , INPUT_POINT AS INPUT_WIDTH
                 , PERIOD AS LABEL_WIDTH
                 , VARIATE
              FROM M4S_I103010
             WHERE USE_YN = 'Y'
               AND DIVISION_CD = '{kwargs['division']}'           
            """
        return sql

    @staticmethod
    def sql_best_hyper_param_grid():
        sql = """
            SELECT STAT_CD
                 , OPTION_CD
                 , OPTION_VAL
              FROM M4S_I103011
            """
        return sql

    @staticmethod
    def sql_err_grp_map():
        sql = """
            SELECT COMM_DTL_CD
                 , ATTR01_VAL
              FROM M4S_I002011
             WHERE COMM_CD = 'ERR_CD'
            """
        return sql

    @staticmethod
    def sql_item_profile():
        sql = """
            SELECT ITEM_CD AS SKU_CD
                 , ITEM_NM AS SKU_NM
                 , BOM_CD
                 , BOM_NM
              FROM M4S_I002043   
        """
        return sql

    @staticmethod
    def sql_exg_data(partial_yn: str):
        sql = f"""
            SELECT IDX_CD
                 , IDX_DTL_CD
                 , YYMM
                 , REF_VAL
              FROM M4S_O110710
             WHERE IDX_CD IN (
                              SELECT IDX_CD
                                FROM M4S_O110700
                               WHERE USE_YN = 'Y'
                                 AND EXG_ID IN (
                                                SELECT EXG_ID
                                                  FROM M4S_O110701
                                                 WHERE USE_YN = 'Y'
                                                 AND PARTIAL_YN = '{partial_yn}'
                                               )
                             )
        """
        return sql

    @staticmethod
    def sql_pred_all(**kwargs):
        sql = f"""
            SELECT DATA_VRSN_CD
                 , DIVISION_CD
                 , STAT_CD
               --  , FKEY
                 , WEEK
                 , YYMMDD
                 , RESULT_SALES AS QTY
                 , CUST_GRP_CD
                 , ITEM_ATTR01_CD AS BIZ_CD
                 , ITEM_ATTR02_CD AS LINE_CD
                 , ITEM_ATTR03_CD AS BRAND_CD
                 , ITEM_ATTR04_CD AS ITEM_CD
                 , ITEM_CD AS SKU_CD
              FROM M4S_I110400
             WHERE DATA_VRSN_CD = '{kwargs['data_vrsn_cd']}'
               AND DIVISION_CD = '{kwargs['division_cd']}'
               AND FKEY LIKE '%{kwargs['fkey']}%'
        """
        return sql

    @staticmethod
    def sql_pred_item(**kwargs):
        sql = f"""
            SELECT DATA_VRSN_CD
                 , DIVISION_CD
                 , ITEM_ATTR01_CD
                 , ITEM_ATTR02_CD
                 , ITEM_ATTR03_CD
                 , ITEM_ATTR04_CD
                 , WEEK
                 , YYMMDD
                 , SUM(RESULT_SALES) AS QTY
              FROM (
                   SELECT DATA_VRSN_CD
                        , DIVISION_CD
                        , WEEK
                        , YYMMDD
                        , RESULT_SALES
                        , ITEM_ATTR01_CD
                        , ITEM_ATTR02_CD
                        , ITEM_ATTR03_CD
                        , ITEM_ATTR04_CD
                        , ITEM_CD
                   FROM M4S_O110600
                   WHERE 1 = 1
                     AND DATA_VRSN_CD = '{kwargs['data_vrsn_cd']}'
                     AND DIVISION_CD = '{kwargs['division_cd']}'
                     AND FKEY LIKE '%{kwargs['fkey']}%'
                     AND ITEM_ATTR04_CD ='{kwargs['item_cd']}'
                  ) PRED
             GROUP BY DATA_VRSN_CD
                    , DIVISION_CD
                    , ITEM_ATTR01_CD
                    , ITEM_ATTR02_CD
                    , ITEM_ATTR03_CD
                    , ITEM_ATTR04_CD
                    , YYMMDD
                    , WEEK
                """
        return sql

    @staticmethod
    def sql_sales_item(**kwargs):
        sql = f"""
            SELECT YYMMDD
                 , RST_SALES_QTY AS QTY_LAG
              FROM M4S_I002175
             WHERE ITEM_ATTR04_CD = '{kwargs['item_cd']}'
               AND YYMMDD BETWEEN '{kwargs['from_date']}' AND '{kwargs['to_date']}'
                """
        return sql

    ###################
    # Delete Query
    ###################
    @staticmethod
    def del_openapi(**kwargs):
        sql = f"""
            DELETE 
              FROM M4S_O110710
             WHERE PROJECT_CD = 'ENT001'
               AND IDX_CD = '{kwargs['idx_cd']}'
               AND IDX_DTL_CD = '{kwargs['idx_dtl_cd']}'
               AND YYMM BETWEEN '{kwargs['api_start_day']}' AND '{kwargs['api_end_day']}'
        """
        return sql

    @staticmethod
    def del_score(**kwargs):
        sql = f"""
            DELETE 
              FROM {kwargs['table_nm']}
             WHERE PROJECT_CD = '{kwargs['project_cd']}'
               AND DATA_VRSN_CD = '{kwargs['data_vrsn_cd']}'
               AND DIVISION_CD = '{kwargs['division_cd']}'
               AND FKEY LIKE '%{kwargs['fkey']}%'
        """
        return sql

    @staticmethod
    def del_prediction(**kwargs):
        sql = f"""
            DELETE
              FROM M4S_I110400
             WHERE PROJECT_CD = '{kwargs['project_cd']}'
               AND DATA_VRSN_CD = '{kwargs['data_vrsn_cd']}'
               AND DIVISION_CD = '{kwargs['division_cd']}'
               AND FKEY LIKE '%{kwargs['fkey']}%'
        """
        return sql

    @staticmethod
    def del_hyper_params(**kwargs):
        sql = f"""
        DELETE
          FROM M4S_I103011
         WHERE PROJECT_CD = '{kwargs['project_cd']}'
           AND STAT_CD = '{kwargs['stat_cd']}'
           AND OPTION_CD = '{kwargs['option_cd']}'
        """
        return sql

    @staticmethod
    def del_compare_result(**kwargs):
        sql = f"""
        DELETE
          FROM M4S_O110620
         WHERE PROJECT_CD = '{kwargs['project_cd']}'
           AND DATA_VRSN_CD = '{kwargs['project_cd']}'
           AND DIVISION_CD = '{kwargs['division_cd']}'
           AND TEST_VRSN_CD = '{kwargs['test_vrsn_cd']}'
        """
        return sql

    ###################
    # Temp Query
    ###################
    # SELL-OUT Table
    @staticmethod
    def sql_sell_out_temp(**kwargs):
        sql = f"""
            SELECT DIVISION_CD
                 , SOLD_CUST_GRP_CD AS CUST_CD
                 , ITEM_CD AS SKU_CD
                 , YYMMDD
                 , SEQ
                 , DISCOUNT
                 , WEEK
                 , RST_SALES_QTY AS QTY
                 , CREATE_DATE
              FROM M4S_I002173
             WHERE YYMMDD BETWEEN '{kwargs['from_date']}' AND '{kwargs['to_date']}'
        """
        return sql

    # SELL-IN Table
    @staticmethod
    def sql_sell_in_test(**kwargs):
        sql = f""" 
            SELECT DIVISION_CD
                 , CUST_GRP_CD
                 , BIZ_CD
                 , LINE_CD
                 , BRAND_CD
                 , ITEM_CD
                 , SALES.SKU_CD 
                 , YYMMDD
                 , SEQ
                 , FROM_DC_CD
                 , UNIT_PRICE
                 , UNIT_CD
                 , DISCOUNT
                 , WEEK
                 , QTY
                 , CREATE_DATE
              FROM (
                    SELECT PROJECT_CD
                         , DIVISION_CD
                         , SOLD_CUST_GRP_CD AS CUST_GRP_CD
                         , ITEM_CD AS SKU_CD
                         , YYMMDD
                         , SEQ
                         , FROM_DC_CD
                         , UNIT_PRICE
                         , RTRIM(UNIT_CD) AS UNIT_CD
                         , DISCOUNT
                         , WEEK
                         , RST_SALES_QTY AS QTY
                         , CREATE_DATE
                      FROM M4S_I002170_TEST
                     WHERE YYMMDD BETWEEN {kwargs['date_from']} AND {kwargs['date_to']}
                     AND RST_SALES_QTY > 0 
                     --and SOLD_CUST_GRP_CD = '1033' -- exception
                    ) SALES
              LEFT OUTER JOIN (
                               SELECT ITEM_CD AS SKU_CD
                                    , ITEM_ATTR01_CD AS BIZ_CD
                                    , ITEM_ATTR02_CD AS LINE_CD
                                    , ITEM_ATTR03_CD AS BRAND_CD
                                    , ITEM_ATTR04_CD AS ITEM_CD
                                 FROM VIEW_I002040
                                WHERE ITEM_TYPE_CD IN ('HAWA', 'FERT')
                              ) ITEM
                ON SALES.SKU_CD = ITEM.SKU_CD
               """

        return sql

    @staticmethod
    def sql_sell_in_unit(**kwargs):
        sql = f""" 
              SELECT DIVISION_CD
                   , CUST_GRP_CD
                   , BIZ_CD
                   , LINE_CD
                   , BRAND_CD
                   , ITEM_CD
                   , SALES.SKU_CD 
                   , YYMMDD
                   , SEQ
                   , FROM_DC_CD
                   , UNIT_PRICE
                   , UNIT_CD
                   , DISCOUNT
                   , WEEK
                   , QTY
                   , CREATE_DATE
                FROM (
                      SELECT PROJECT_CD
                           , DIVISION_CD
                           , SOLD_CUST_GRP_CD AS CUST_GRP_CD
                           , ITEM_CD AS SKU_CD
                           , YYMMDD
                           , SEQ
                           , FROM_DC_CD
                           , UNIT_PRICE
                           , RTRIM(UNIT_CD) AS UNIT_CD
                           , DISCOUNT
                           , WEEK
                           , RST_SALES_QTY AS QTY
                           , CREATE_DATE
                        FROM M4S_I002170_TEST
                       WHERE YYMMDD BETWEEN {kwargs['date_from']} AND {kwargs['date_to']}
                       AND RST_SALES_QTY > 0 
                       AND SOLD_CUST_GRP_CD = '{kwargs['cust_grp_cd']}',
                       AND ITEM_CD = '{kwargs['item_cd']}'
                       --and SOLD_CUST_GRP_CD = '1033' -- exception
                      ) SALES
                LEFT OUTER JOIN (
                                 SELECT ITEM_CD AS SKU_CD
                                      , ITEM_ATTR01_CD AS BIZ_CD
                                      , ITEM_ATTR02_CD AS LINE_CD
                                      , ITEM_ATTR03_CD AS BRAND_CD
                                      , ITEM_ATTR04_CD AS ITEM_CD
                                   FROM VIEW_I002040
                                  WHERE ITEM_TYPE_CD IN ('HAWA', 'FERT')
                                ) ITEM
                  ON SALES.SKU_CD = ITEM.SKU_CD
                 """

        return sql

    @staticmethod
    def sql_sell_in_temp(**kwargs):
        sql = f""" 
               SELECT DIVISION_CD
                    , SOLD_CUST_GRP_CD AS CUST_GRP_CD
                    , SKU_CD
                    , YY
                    , WEEK
                    , SUM(RST_SALES_QTY) AS SALES
                 FROM (
                       SELECT DIVISION_CD
                            , SOLD_CUST_GRP_CD
                            , SKU_CD
                            , YY
                            , WEEK
                            , CASE WHEN UNIT_CD = 'BOX' THEN RST_SALES_QTY
                                   WHEN UNIT_CD = 'EA' THEN ROUND(RST_SALES_QTY / BOX_EA, 2)
                                   WHEN UNIT_CD = 'BOL' THEN ROUND(RST_SALES_QTY / BOX_BOL, 2)
                                   ELSE 0
                                    END AS RST_SALES_QTY
                         FROM (
                               SELECT DIVISION_CD
                                    , SOLD_CUST_GRP_CD
                                    , SALES.SKU_CD
                                    , YY
                                    , WEEK
                                    , UNIT_CD
                                    , BOX_BOL
                                    , BOX_EA
                                    , RST_SALES_QTY
                                 FROM (
                                       SELECT DIVISION_CD
                                            , SOLD_CUST_GRP_CD
                                            , ITEM_CD as SKU_CD
                                            , YY
                                            , WEEK
                                            , UNIT_CD
                                            , RST_SALES_QTY
                                        FROM  M4S_I002170_TEST
                                       WHERE 1=1
                                         AND YYMMDD BETWEEN '{kwargs['date_from']}' AND '{kwargs['date_to']}'
                                         AND RST_SALES_QTY > 0    -- Remove minus quantity
                                         --AND SOLD_CUST_GRP_CD = '1033' -- exception
                                     ) SALES
                         LEFT OUTER JOIN (
                                          SELECT BOX.ITEM_CD                                 AS SKU_CD
                                               , CONVERT(INT, BOX.FAC_PRICE / BOL.FAC_PRICE) AS BOX_BOL
                                               , CONVERT(INT, BOX.FAC_PRICE / EA.FAC_PRICE)  AS BOX_EA
                                            FROM (
                                                  SELECT PROJECT_CD
                                                       , ITEM_CD
                                                       , PRICE_START_YYMMDD
                                                       , FAC_PRICE
                                                    FROM M4S_I002041
                                                   WHERE PRICE_QTY_UNIT_CD = 'BOX'
                                                     AND FAC_PRICE <> 0
                                                 ) BOX
                                            LEFT OUTER JOIN (
                                                             SELECT PROJECT_CD
                                                                  , ITEM_CD
                                                                  , PRICE_START_YYMMDD
                                                                  , FAC_PRICE
                                                               FROM M4S_I002041
                                                              WHERE PRICE_QTY_UNIT_CD = 'BOL'
                                                                AND FAC_PRICE <> 0
                                                            ) BOL
                                              ON BOX.PROJECT_CD = BOL.PROJECT_CD
                                             AND BOX.ITEM_CD = BOL.ITEM_CD
                                             AND BOX.PRICE_START_YYMMDD = BOL.PRICE_START_YYMMDD
                                            LEFT OUTER JOIN (
                                                             SELECT PROJECT_CD
                                                                  , ITEM_CD
                                                                  , PRICE_START_YYMMDD
                                                                  , FAC_PRICE
                                                               FROM M4S_I002041
                                                              WHERE PRICE_QTY_UNIT_CD = 'EA'
                                                                AND FAC_PRICE <> 0
                                                            ) EA
                                              ON BOX.PROJECT_CD = EA.PROJECT_CD
                                             AND BOX.ITEM_CD = EA.ITEM_CD
                                             AND BOX.PRICE_START_YYMMDD = EA.PRICE_START_YYMMDD
                                         ) UNIT
                           ON SALES.SKU_CD = UNIT.SKU_CD
                           ) SALES
                      ) SALES
                 GROUP BY DIVISION_CD
                        , SOLD_CUST_GRP_CD
                        , SKU_CD
                        , YY
                        , WEEK
                """
        return sql

    @staticmethod
    def sql_item_mst_sell_out_temp():
        sql = """
              SELECT SKU_CD
                   , SKU_NM
                FROM (
                      SELECT SKU_CD
                           , SKU_NM
                           , ROW_NUMBER() over (PARTITION BY SKU_CD ORDER BY SKU_NM) AS DUP
                        FROM (
                              SELECT SELL_BARCD AS SKU_CD
                                   , PROD_NM    AS SKU_NM
                                FROM TEST_NEW.dbo.SELLOUT_PAST_HOME_MASTER
                               GROUP BY SELL_BARCD
                                      , PROD_NM
                             ) ITEM_MST
                     ) ITEM_MST
              WHERE DUP = 1  
            """
        return sql