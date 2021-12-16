import datetime


class Cycle(object):
    def __init__(self, common: dict, rule):
        self.common = common
        self.rule = rule    # w / m

        # Timeline Configuration
        self.hist_period = ()    # History period (history_start, history_end)
        self.eval_period = ()    # Evaluation period (evaluation_start, evaluation_end)
        self.pred_period = ()    # Forecast period (forecast_start, forecast_end)

    def calc_period(self) -> None:
        today = datetime.date.today()

        hist_from, hist_to = (None, None)
        eval_from, eval_to = (None, None)
        pred_from, pred_to = (None, None)

        if self.rule == 'w':
            # Period: Sales History
            hist_from = today - datetime.timedelta(days=self.common['hist_week'] * 7)
            hist_to = today - datetime.timedelta(days=1)

            # Period: Evaluation
            eval_from = today - datetime.timedelta(days=self.common['eval_week'] * 7)
            eval_to = today - datetime.timedelta(days=1)

            # Period: Forecast
            pred_from = today    # Monday
            pred_to = today + datetime.timedelta(days=self.common['pred_week'] * 7 - 1)

        elif self.rule == 'm':
            # Period: Sales History
            hist_from = self.last_day_of_month(today - datetime.timedelta(days=self.common['hist_mon'] * 28))
            hist_to = today - datetime.timedelta(days=1)

            # Period: Evaluation
            eval_from = self.last_day_of_month(today - datetime.timedelta(days=self.common['eval_mon'] * 28))
            eval_to = today - datetime.timedelta(days=1)

            # Period: Forecast
            pred_from = today    # Monday
            pred_to = self.last_day_of_month(today + datetime.timedelta(days=self.common['pred_mon'] * 28))

        self.hist_period = (hist_from, hist_to)
        self.eval_period = (eval_from, eval_to)
        self.pred_period = (pred_from, pred_to)

    @staticmethod
    def last_day_of_month(date):
        next_month = date.replace(day=28) + datetime.timedelta(days=4)
        last_day = next_month - datetime.timedelta(days=next_month.day)

        return last_day