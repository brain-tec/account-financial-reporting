# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright Camptocamp SA 2011
#    SQL inspired from OpenERP original code
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from operator import add
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import ustr
from .common_reports import CommonReportHeaderWebkit


class CommonBalanceReportHeaderWebkit(CommonReportHeaderWebkit):

    """Define common helper for balance (trial balance, P&L, BS oriented
       financial report"""

    def _get_numbers_display(self, data):
        return self._get_form_param('numbers_display', data)

    @staticmethod
    def find_key_by_value_in_list(dic, value):
        return [key for key, val in dic.iteritems() if value in val][0]

    def _get_account_details(self, account_ids, target_move, fiscalyear,
                             main_filter, start, stop, initial_balance_mode, from_er_detail=False,
                             context=None):
        """
        Get details of accounts to display on the report
        @param account_ids: ids of accounts to get details
        @param target_move: selection filter for moves (all or posted)
        @param fiscalyear: browse of the fiscalyear
        @param main_filter: selection filter period / date or none
        @param start: start date or start period browse instance
        @param stop: stop date or stop period browse instance
        @param initial_balance_mode: False: no calculation,
               'opening_balance': from the opening period,
               'initial_balance': computed from previous year / periods
        @return: dict of list containing accounts details, keys are
                 the account ids
        """
        if context is None:
            context = {}

        account_obj = self.pool.get('account.account')
        period_obj = self.pool.get('account.period')
        use_period_ids = main_filter in (
            'filter_no', 'filter_period', 'filter_opening')

        if use_period_ids:
            if main_filter == 'filter_opening':
                period_ids = [start.id]
            else:
                period_ids = period_obj.build_ctx_periods(
                    self.cursor, self.uid, start.id, stop.id)
                # never include the opening in the debit / credit amounts
                period_ids = self.exclude_opening_periods(period_ids)

        init_balance = False
        if initial_balance_mode == 'opening_balance':
            init_balance = self._read_opening_balance(account_ids, start)
        elif initial_balance_mode:
            init_balance = self._compute_initial_balances(
                account_ids, start, fiscalyear)

        ctx = context.copy()
        ctx.update({'state': target_move,
                    'all_fiscalyear': True})

        if use_period_ids:
            ctx.update({'periods': period_ids})
        elif main_filter == 'filter_date':
            ctx.update({'date_from': start,
                        'date_to': stop})

        accounts = account_obj.read(
            self.cursor,
            self.uid,
            account_ids,
            ['type', 'code', 'name', 'debit', 'credit',
                'balance', 'parent_id', 'level', 'child_id'],
            context=ctx)

        accounts_by_id = {}
        for account in accounts:
            child_ids = account_obj._get_children_and_consol(
                self.cursor, self.uid, account['id'], ctx)
            if init_balance:
                # sum for top level views accounts
                if child_ids:
                    child_init_balances = [
                        init_bal['init_balance']
                        for acnt_id, init_bal in init_balance.iteritems()
                        if acnt_id in child_ids]
                    top_init_balance = reduce(add, child_init_balances)
                    account['init_balance'] = top_init_balance
                else:
                    account.update(init_balance[account['id']])
                account['balance'] = account['init_balance'] + \
                    account['debit'] - account['credit']
            # set budget for each account for each month
            if from_er_detail:
                # TODO: 07.08.17 14:10: jool1: only do this when called from ER Detail wizard
                planned_months = {}
                budget_period_ids = []
                if fiscalyear:
                    budget_period_ids = self.exclude_opening_periods(fiscalyear.period_ids.ids)
                planned_amounts = 0

                for period in period_obj.browse(self.cr, self.uid, budget_period_ids):
                    child_ids_objs = self.pool.get('account.account').browse(
                        self.cursor,
                        self.uid,
                        child_ids,
                        context=self.localcontext)
                    child_ids_codes = tuple([child_obj.code for child_obj in child_ids_objs])

                    date_format = "%Y-%m-%d"
                    date_lower = period.date_start
                    date_upper = period.date_stop

                    # jool1 Method to get budget
#                     self.cr.execute(
#                         """select sum(planned_amount) as sum_planned_amount from crossovered_budget_lines where general_budget_id in (select id from account_budget_post where name in %s) and (date_from between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd'))
# and (date_to between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd'))""",
#                         (child_ids_codes, period.date_start, period.date_stop, period.date_start, period.date_stop))
#
#                     sum_budget = float(self.cr.fetchone()[0] or 0)

                    ### HACK by BT-mgerecke
                    # Budgets are monthly but may be any timespan.
                    # Attention! For Valaiscom the account code is stored in column name not in column code.
                    # Get all touched budgets of periode
                    self.cr.execute("SELECT planned_amount,date_from,date_to,id FROM crossovered_budget_lines"
                                    " WHERE general_budget_id IN (SELECT id FROM account_budget_post WHERE name in %s)"
                                    " AND ((date_from between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd'))"
                                    "   OR (date_to between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd')))",
                                    (child_ids_codes, date_lower, date_upper, date_lower, date_upper))
                    budgets_raw = self.cr.fetchall()
                    # Jump to next iteration if no budget was found.
                    if not budgets_raw:
                        planned_months[int(period.code[0:2])] = 0
                        continue
                    elif isinstance(budgets_raw, tuple):
                        planned_months[int(period.code[0:2])] = 0
                        continue
                    elif not budgets_raw[0]:
                        planned_months[int(period.code[0:2])] = 0
                        continue

                    datetime_lower = datetime.strptime(date_lower, date_format)
                    datetime_upper = datetime.strptime(date_upper, date_format)
                    sum_budget = 0.0
                    # Check each budget if it can be fully or partly added.
                    for bgt in budgets_raw:
                        datetime_bgt_lower = datetime.strptime(bgt[1], date_format)
                        datetime_bgt_upper = datetime.strptime(bgt[2], date_format)
                        # Calculate timespan of budget in days
                        bgt_days = (datetime_bgt_upper - datetime_bgt_lower).days + 1.0
                        bgt_days_real = bgt_days
                        # Calculate how many days of the budget are outside the choosen timespan.
                        bgt_days_l_diff = (datetime_bgt_lower - datetime_lower).days
                        bgt_days_u_diff = (datetime_upper - datetime_bgt_upper).days
                        # Remove budget days outside of choosen timespan (before and after).
                        for days_remove in (bgt_days_l_diff, bgt_days_u_diff):
                            if days_remove < 0:
                                bgt_days_real += days_remove
                        # Calculate budget part based on the remaining days and sum it up.
                        bgt_real = bgt[0] * (bgt_days_real / bgt_days)
                        sum_budget += bgt_real

                    planned_amounts += sum_budget
                    if int(period.code[0:2]) not in planned_months:
                        planned_months[int(period.code[0:2])] = sum_budget
                    else:
                        planned_months[int(period.code[0:2])] += sum_budget

                account['budget'] = planned_months
                account['budget_total'] = planned_amounts
            accounts_by_id[account['id']] = account
        return accounts_by_id

    def _get_comparison_details(self, data, account_ids, target_move,
                                comparison_filter, index):
        """

        @param data: data of the wizard form
        @param account_ids: ids of the accounts to get details
        @param comparison_filter: selected filter on the form for
               the comparison (filter_no, filter_year, filter_period,
                               filter_date)
        @param index: index of the fields to get
                (ie. comp1_fiscalyear_id where 1 is the index)
        @return: dict of account details (key = account id)
        """
        fiscalyear = self._get_info(
            data, "comp%s_fiscalyear_id" % (index,), 'account.fiscalyear')
        start_period = self._get_info(
            data, "comp%s_period_from" % (index,), 'account.period')
        stop_period = self._get_info(
            data, "comp%s_period_to" % (index,), 'account.period')
        start_date = self._get_form_param("comp%s_date_from" % (index,), data)
        stop_date = self._get_form_param("comp%s_date_to" % (index,), data)
        init_balance = self.is_initial_balance_enabled(comparison_filter)

        accounts_by_ids = {}
        comp_params = {}
        details_filter = comparison_filter
        if comparison_filter != 'filter_no':
            start_period, stop_period, start, stop = \
                self._get_start_stop_for_filter(
                    comparison_filter, fiscalyear, start_date, stop_date,
                    start_period, stop_period)
            if comparison_filter == 'filter_year':
                details_filter = 'filter_no'

            ctx = {'journal_ids': data['form']['used_context']['journal_ids']}
            initial_balance_mode = init_balance \
                and self._get_initial_balance_mode(start) or False
            accounts_by_ids = self._get_account_details(
                account_ids, target_move, fiscalyear, details_filter,
                start, stop, initial_balance_mode, context=ctx)
            comp_params = {
                'comparison_filter': comparison_filter,
                'fiscalyear': fiscalyear,
                'start': start,
                'stop': stop,
                'initial_balance': init_balance,
                'initial_balance_mode': initial_balance_mode,
            }

        return accounts_by_ids, comp_params

    def _get_diff(self, balance, previous_balance):
        """
        @param balance: current balance
        @param previous_balance: last balance
        @return: dict of form {'diff': difference,
                               'percent_diff': diff in percentage}
        """
        diff = balance - previous_balance

        obj_precision = self.pool.get('decimal.precision')
        precision = obj_precision.precision_get(
            self.cursor, self.uid, 'Account')
        # round previous balance with account precision to avoid big numbers
        # if previous balance is 0.0000001 or a any very small number
        if round(previous_balance, precision) == 0:
            percent_diff = False
        else:
            percent_diff = round(diff / previous_balance * 100, precision)

        return {'diff': diff, 'percent_diff': percent_diff}

    def _comp_filters(self, data, comparison_number):
        """
        @param data: data of the report
        @param comparison_number: number of comparisons
        @return: list of comparison filters, nb of comparisons used and
                 comparison mode (no_comparison, single, multiple)
        """
        comp_filters = []
        for index in range(comparison_number):
            comp_filters.append(
                self._get_form_param("comp%s_filter" % (index,), data,
                                     default='filter_no'))

        nb_comparisons = len(
            [comp_filter for comp_filter in comp_filters
                if comp_filter != 'filter_no'])
        if not nb_comparisons:
            comparison_mode = 'no_comparison'
        elif nb_comparisons > 1:
            comparison_mode = 'multiple'
        else:
            comparison_mode = 'single'
        return comp_filters, nb_comparisons, comparison_mode

    def _get_start_stop_for_filter(self, main_filter, fiscalyear, start_date,
                                   stop_date, start_period, stop_period):
        if main_filter in ('filter_no', 'filter_year'):
            start_period = self.get_first_fiscalyear_period(fiscalyear)
            stop_period = self.get_last_fiscalyear_period(fiscalyear)
        elif main_filter == 'filter_opening':
            opening_period = self._get_st_fiscalyear_period(
                fiscalyear, special=True)
            start_period = stop_period = opening_period
        if main_filter == 'filter_date':
            start = start_date
            stop = stop_date
        else:
            start = start_period
            stop = stop_period

        return start_period, stop_period, start, stop

    def get_lines(self, data, main_filter, use_period_ids):
        lines = []
        account_obj = self.pool.get('account.account')
        ids2 = self.pool.get('account.financial.report')._get_children_by_order(self.cr, self.uid, [
            data['form']['account_report_id'][0]], context=data['form']['used_context'])
        all_account_ids = []
        report_account_ids = dict()
        for report in self.pool.get('account.financial.report').browse(self.cr, self.uid, ids2,
                                                                       context=data['form']['used_context']):
            vals = {
                'code': len(report.account_ids) == 1 and report.account_ids.code or '',
                'name': report.name,
                'balance': report.balance * report.sign or 0.0,
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type == 'sum' and 'view' or 'view',
                # 'account_id': False,
                'account_id': len(report.account_ids) == 1 and report.account_ids.id or '',
                'child_consol_ids': [],
                # used to underline the financial report balances
                'c_rechnung_actual_year': 0,
                'e_budget_actual_year': 0,
                'g_rechnung_previous_year': 0,
                'i_forecast_previous_quarter': 0,
                'report_id': report.id,
                'values_need_to_be_updated': True,
            }
            # do not append ERFOLGSRECHNUNG as first line
            if data['form']['account_report_id'][1] != report.name:
                lines.append(vals)
            account_ids = []
            if report.display_detail == 'no_detail':
                # the rest of the loop is used to display the details of the financial report, so it's not needed here.
                all_account_ids += [x.id for x in report.account_ids]
                # HACK: 04.08.17 08:17: jool1: add account_id to report_account_ids
                for account in report.account_ids:
                    child_ids = account_obj._get_children_and_consol(
                        self.cursor, self.uid, account.id)
                    for account in account_obj.browse(self.cr, self.uid, child_ids,
                                                      context=data['form']['used_context']):
                        if account.type != 'view' and account.type != 'consolidation':
                            if report.id in report_account_ids:
                                report_account_ids[report.id].append(account.id)
                            else:
                                report_account_ids[report.id] = [account.id]
                continue
            if report.type == 'accounts' and report.account_ids:
                account_ids = account_obj._get_children_and_consol(self.cr, self.uid,
                                                                   [x.id for x in report.account_ids])
            elif report.type == 'account_type' and report.account_type_ids:
                account_ids = account_obj.search(self.cr, self.uid,
                                                 [('user_type', 'in', [x.id for x in report.account_type_ids])])
            if account_ids:
                all_account_ids += account_ids

                for account in account_obj.browse(self.cr, self.uid, account_ids,
                                                  context=data['form']['used_context']):
                    # if there are accounts to display, we add them to the lines with a level equals to their level in
                    # the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                    # financial reports for Assets, liabilities...)
                    if report.display_detail == 'detail_flat' and account.type == 'view':
                        continue
                    flag = False
                    vals = {
                        'code': account.code,
                        # 'name': account.code + ' ' + account.name,
                        'name': account.name,
                        'balance': account.balance != 0 and account.balance * report.sign or account.balance,
                        'type': 'account',
                        # 'level': report.display_detail == 'detail_with_hierarchy' and min(account.level + 1,
                        #                                                                   6) or 6,
                        'level': account.level,
                        # 'level': accounts_by_ids[account.id]['level'],
                        'account_type': account.type,
                        # 'account_type': 'other',
                        'child_consol_ids': account.child_consol_ids,
                        'account_id': account.id,
                        'c_rechnung_actual_year': 0,
                        'e_budget_actual_year': 0,
                        'g_rechnung_previous_year': 0,
                        'i_forecast_previous_quarter': 0,
                        'report_id': report.id,
                        'values_need_to_be_updated': False,
                    }
                    # HACK: 04.08.17 08:17: jool1: add account_id to report_account_ids
                    if account.type != 'view' and account.type != 'consolidation':
                        if report.id in report_account_ids:
                            report_account_ids[report.id].append(account.id)
                        else:
                            report_account_ids[report.id] = [account.id]

                    lines.append(vals)
        return all_account_ids, lines, report_account_ids

    def compute_balance_data_er_detail(self, data, filter_report_type=None):
        new_ids = data['form']['account_ids'] or data[
            'form']['chart_account_id']
        max_comparison = self._get_form_param(
            'max_comparison', data, default=0)
        main_filter = self._get_form_param('filter', data, default='filter_no')

        # comp_filters, nb_comparisons, comparison_mode = self._comp_filters(
        #     data, max_comparison)
        #set hardcoded and ignore all manual entries in wizard
        use_period_ids = main_filter in (
            'filter_no', 'filter_period', 'filter_opening')
        if use_period_ids:
            comp_filters = ['filter_period', 'filter_no', 'filter_no']
        elif main_filter == 'filter_date':
            comp_filters = ['filter_date', 'filter_no', 'filter_no']
        nb_comparisons = 1
        comparison_mode = 'single'

        fiscalyear = self.get_fiscalyear_br(data)

        start_period = self.get_start_period_br(data)
        stop_period = self.get_end_period_br(data)

        target_move = self._get_form_param('target_move', data, default='all')
        start_date = self._get_form_param('date_from', data)
        stop_date = self._get_form_param('date_to', data)
        chart_account = self._get_chart_account_id_br(data)

        start_period, stop_period, start, stop = \
            self._get_start_stop_for_filter(main_filter, fiscalyear,
                                            start_date, stop_date,
                                            start_period, stop_period)
        init_balance = self.is_initial_balance_enabled(main_filter)
        initial_balance_mode = init_balance and self._get_initial_balance_mode(
            start) or False
        # TODO: 04.08.17 10:41: jool1: get id of "ERFOLGSRECHNUNG Detail"
        data['form']['account_report_id'] = [104, u'ERFOLGSRECHNUNG Detail']
        account_ids, lines, report_account_ids = self.get_lines(data, main_filter, use_period_ids)

        ctx = {'journal_ids': data['form']['used_context']['journal_ids']}
        # get details for each accounts, total of debit / credit / balance
        accounts_by_ids = self._get_account_details(
            account_ids, target_move, fiscalyear, main_filter, start, stop,
            initial_balance_mode, True, context=ctx)

        # HACK: 04.08.17 14:04: jool1: accounts_forecast_by_ids (stop minus 3 months)
        accounts_forecast_by_ids = []
        index_forecast_stop = 0
        data_forecast = data.copy()
        if use_period_ids:
            # substract 3 months
            fiscalyear_exluded_opening_period_ids = self.exclude_opening_periods(fiscalyear.period_ids.ids)
            index_stop_id = fiscalyear_exluded_opening_period_ids.index(stop.id)
            forecast_stop = index_stop_id - 3
            if forecast_stop > 0:
                index_forecast_stop_id = fiscalyear_exluded_opening_period_ids[forecast_stop]
                index_forecast_stop = self.pool.get('account.period').browse(self.cr, self.uid, index_forecast_stop_id)
                data_forecast['form']['used_context']['period_to'] = index_forecast_stop_id
                accounts_forecast_by_ids = self._get_account_details(
                    account_ids, target_move, fiscalyear, main_filter, start, index_forecast_stop,
                    initial_balance_mode, False, context=ctx)
        elif main_filter == 'filter_date':
            # substract 3 months
            d = datetime.strptime(ustr(stop_date), "%Y-%m-%d")
            d = d + relativedelta(days=1)
            d = d - relativedelta(months=3)
            stop_date_minus_3_months = d - relativedelta(days=1)
            first_day_of_year = datetime(int(d.year), 01, 01)
            if stop_date_minus_3_months >= first_day_of_year:
                data_forecast['form']['used_context']['date_to'] = stop_date_minus_3_months
                accounts_forecast_by_ids = self._get_account_details(
                    account_ids, target_move, fiscalyear, main_filter, start, stop_date_minus_3_months,
                    initial_balance_mode, False, context=ctx)

        comparison_params = []
        comp_accounts_by_ids = []
        # set hardcoded and ignore all manual entries in wizard
        index = 0
        data['form']['comp0_fiscalyear_id'] = False
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        last_fiscalyear_id = fiscalyear_obj.search(self.cr, self.uid,
                                                   [('code', '=', int(fiscalyear.code) - 1)])
        last_fiscalyear = fiscalyear_obj.browse(self.cr, self.uid, last_fiscalyear_id[0])
        if use_period_ids:
            data['form']['comp0_filter'] = 'filter_period'
            last_fiscalyear_period_ids = self.exclude_opening_periods(last_fiscalyear.period_ids.ids)
            data['form']['comp0_period_from'] = last_fiscalyear_period_ids[0] #15
            data['form']['comp0_period_to'] = last_fiscalyear_period_ids[len(last_fiscalyear_period_ids)-1] #26
        elif main_filter == 'filter_date':
            data['form']['comp0_filter'] = 'filter_date'
            data['form']['comp0_date_from'] = last_fiscalyear.date_start
            data['form']['comp0_date_to'] = last_fiscalyear.date_stop

        comparison_result, comp_params = self._get_comparison_details(
            data, account_ids, target_move, comp_filters[index], index)
        comparison_params.append(comp_params)
        comp_accounts_by_ids.append(comparison_result)

        objects = self.pool.get('account.account').browse(
            self.cursor,
            self.uid,
            account_ids,
            context=self.localcontext)

        to_display_accounts = dict.fromkeys(account_ids, True)
        init_balance_accounts = dict.fromkeys(account_ids, False)
        comparisons_accounts = dict.fromkeys(account_ids, [])
        debit_accounts = dict.fromkeys(account_ids, False)
        credit_accounts = dict.fromkeys(account_ids, False)
        balance_accounts = dict.fromkeys(account_ids, False)
        budget_accounts = dict.fromkeys(account_ids, False)
        balance_forecast_accounts = dict.fromkeys(account_ids, False)

        for account in objects:
            if account.type == 'consolidation':
                to_display_accounts.update(
                    dict([(a.id, False) for a in account.child_consol_ids]))
            elif account.type == 'view':
                to_display_accounts.update(
                    dict([(a.id, True) for a in account.child_id]))
            debit_accounts[account.id] = \
                accounts_by_ids[account.id]['debit']
            credit_accounts[account.id] = \
                accounts_by_ids[account.id]['credit']
            balance_accounts[account.id] = \
                accounts_by_ids[account.id]['balance']
            if account.id in accounts_forecast_by_ids:
                balance_forecast_accounts[account.id] = \
                    accounts_forecast_by_ids[account.id]['balance']
            # budget_accounts add budget for rest of months
            budget_until_end_of_year = 0
            budget_until_end_of_year_minus_3_months = 0
            if use_period_ids:
                dt = datetime.strptime(stop.date_start, '%Y-%m-%d')
            else:
                dt = datetime.strptime(stop_date, '%Y-%m-%d')
            for budget_month in accounts_by_ids[account.id]['budget']:
                if budget_month > dt.month:
                    budget_until_end_of_year += accounts_by_ids[account.id]['budget'][budget_month]
                if budget_month > dt.month-3:
                    budget_until_end_of_year_minus_3_months += accounts_by_ids[account.id]['budget'][budget_month]

            balance_accounts[account.id] += budget_until_end_of_year
            budget_accounts[account.id] = \
                accounts_by_ids[account.id]['budget_total']
            balance_forecast_accounts[account.id] += budget_until_end_of_year_minus_3_months
            # init_balance_accounts
            init_balance_accounts[account.id] = \
                accounts_by_ids[account.id].get('init_balance', 0.0)

            # if any amount is != 0 in comparisons, we have to display the
            # whole account
            display_account = False
            for comp_account_by_id in comp_accounts_by_ids:
                values = comp_account_by_id.get(account.id)
                values.update(
                    self._get_diff(balance_accounts[account.id], values['balance']))
                display_account = values.get('balance', 0.0) != 0
                comparisons_accounts[account.id] = \
                    values.get('balance', 0.0)
            # we have to display the account if a comparison as an amount or
            # if we have an amount in the main column
            # we set it as a property to let the data in the report if someone
            # want to use it in a custom report
            display_account = display_account \
                              or any((debit_accounts[account.id],
                                      credit_accounts[account.id],
                                      balance_accounts[account.id],
                                      budget_accounts[account.id],
                                      balance_forecast_accounts[account.id],
                                      init_balance_accounts[account.id]))
            to_display_accounts.update(
                {account.id: display_account and
                             to_display_accounts[account.id]})

        # set balance_totals_per_report_id
        balance_totals_per_report_id = dict()
        for report_account_id in report_account_ids:
            sum_per_report_account_id = 0
            for balance_account in balance_accounts:
                if balance_account in report_account_ids[report_account_id]:
                    sum_per_report_account_id += balance_accounts[balance_account]
            balance_totals_per_report_id[report_account_id] = sum_per_report_account_id

        # set budgets_totals_per_report_id
        budgets_totals_per_report_id = dict()
        for report_account_id in report_account_ids:
            sum_per_report_account_id = 0
            for budget_account in budget_accounts:
                if budget_account in report_account_ids[report_account_id]:
                    sum_per_report_account_id += budget_accounts[budget_account]
            budgets_totals_per_report_id[report_account_id] = sum_per_report_account_id

        # set comparisons_totals_per_report_id
        comparisons_totals_per_report_id = dict()
        for report_account_id in report_account_ids:
            sum_per_report_account_id = 0
            for comparisons_account in comparisons_accounts:
                if comparisons_account in report_account_ids[report_account_id]:
                    sum_per_report_account_id += comparisons_accounts[comparisons_account]
            comparisons_totals_per_report_id[report_account_id] = sum_per_report_account_id

        # set balance_forecast_accounts_totals_per_report_id
        balance_forecast_accounts_totals_per_report_id = dict()
        for report_account_id in report_account_ids:
            sum_per_report_account_id = 0
            for balance_forecast_account in balance_forecast_accounts:
                if balance_forecast_account in report_account_ids[report_account_id]:
                    sum_per_report_account_id += balance_forecast_accounts[balance_forecast_account]
            balance_forecast_accounts_totals_per_report_id[report_account_id] = sum_per_report_account_id

        # update values for total lines (line like BRUTTOGEWINN)
        for line_to_update in lines:
            if line_to_update['values_need_to_be_updated'] and line_to_update['report_id'] in balance_totals_per_report_id:
                line_to_update['c_rechnung_actual_year'] = balance_totals_per_report_id[line_to_update['report_id']]
            if line_to_update['values_need_to_be_updated'] and line_to_update['report_id'] in budgets_totals_per_report_id:
                line_to_update['e_budget_actual_year'] = budgets_totals_per_report_id[line_to_update['report_id']]
            if line_to_update['values_need_to_be_updated'] and line_to_update['report_id'] in comparisons_totals_per_report_id:
                line_to_update['g_rechnung_previous_year'] = comparisons_totals_per_report_id[line_to_update['report_id']]
            if line_to_update['values_need_to_be_updated'] and line_to_update['report_id'] in balance_forecast_accounts_totals_per_report_id:
                line_to_update['i_forecast_previous_quarter'] = balance_forecast_accounts_totals_per_report_id[line_to_update['report_id']]

        # set d_rechnung_actual_year_percent
        account_obj = self.pool.get('account.account')
        betriebsertrag_account_id = account_obj.search(self.cr, self.uid, [('code', '=', 3)])
        amount_betriebsertrag = balance_accounts[betriebsertrag_account_id[0]]
        balance_accounts_percent = dict.fromkeys(account_ids, False)
        for balance_account in balance_accounts:
            balance_accounts_percent[balance_account] = balance_accounts[balance_account] / amount_betriebsertrag * 100

        context_report_values = {
            'fiscalyear': fiscalyear,
            'start_date': start_date,
            'stop_date': stop_date,
            'start_period': start_period,
            'stop_period': stop_period,
            'chart_account': chart_account,
            'comparison_mode': comparison_mode,
            'nb_comparison': nb_comparisons,
            'initial_balance': init_balance,
            'initial_balance_mode': initial_balance_mode,
            'comp_params': comparison_params,
            'to_display_accounts': to_display_accounts,
            'init_balance_accounts': init_balance_accounts,
            'comparisons_accounts': comparisons_accounts,
            'debit_accounts': debit_accounts,
            'credit_accounts': credit_accounts,
            'balance_accounts': balance_accounts,
            'budget_accounts': budget_accounts,
            'lines': lines,
            'balance_accounts_percent': balance_accounts_percent,
            'balance_forecast_accounts': balance_forecast_accounts,
            'amount_betriebsertrag': amount_betriebsertrag, # help field to calculate percentage in the report when account.id is missing
        }
        return objects, new_ids, context_report_values

    def compute_balance_data(self, data, filter_report_type=None):
        new_ids = data['form']['account_ids'] or data[
            'form']['chart_account_id']
        max_comparison = self._get_form_param(
            'max_comparison', data, default=0)
        main_filter = self._get_form_param('filter', data, default='filter_no')

        comp_filters, nb_comparisons, comparison_mode = self._comp_filters(
            data, max_comparison)

        fiscalyear = self.get_fiscalyear_br(data)

        start_period = self.get_start_period_br(data)
        stop_period = self.get_end_period_br(data)

        target_move = self._get_form_param('target_move', data, default='all')
        start_date = self._get_form_param('date_from', data)
        stop_date = self._get_form_param('date_to', data)
        chart_account = self._get_chart_account_id_br(data)

        start_period, stop_period, start, stop = \
            self._get_start_stop_for_filter(main_filter, fiscalyear,
                                            start_date, stop_date,
                                            start_period, stop_period)

        init_balance = self.is_initial_balance_enabled(main_filter)
        initial_balance_mode = init_balance and self._get_initial_balance_mode(
            start) or False

        # Retrieving accounts
        account_ids = self.get_all_accounts(
            new_ids, only_type=filter_report_type)

        ctx = {'journal_ids': data['form']['used_context']['journal_ids']}
        # get details for each accounts, total of debit / credit / balance
        accounts_by_ids = self._get_account_details(
            account_ids, target_move, fiscalyear, main_filter, start, stop,
            initial_balance_mode, context=ctx)

        comparison_params = []
        comp_accounts_by_ids = []
        for index in range(max_comparison):
            if comp_filters[index] != 'filter_no':
                comparison_result, comp_params = self._get_comparison_details(
                    data, account_ids, target_move, comp_filters[index], index)
                comparison_params.append(comp_params)
                comp_accounts_by_ids.append(comparison_result)

        objects = self.pool.get('account.account').browse(
            self.cursor,
            self.uid,
            account_ids,
            context=self.localcontext)

        to_display_accounts = dict.fromkeys(account_ids, True)
        init_balance_accounts = dict.fromkeys(account_ids, False)
        comparisons_accounts = dict.fromkeys(account_ids, [])
        debit_accounts = dict.fromkeys(account_ids, False)
        credit_accounts = dict.fromkeys(account_ids, False)
        balance_accounts = dict.fromkeys(account_ids, False)

        for account in objects:
            if account.type == 'consolidation':
                to_display_accounts.update(
                    dict([(a.id, False) for a in account.child_consol_ids]))
            elif account.type == 'view':
                to_display_accounts.update(
                    dict([(a.id, True) for a in account.child_id]))
            debit_accounts[account.id] = \
                accounts_by_ids[account.id]['debit']
            credit_accounts[account.id] = \
                accounts_by_ids[account.id]['credit']
            balance_accounts[account.id] = \
                accounts_by_ids[account.id]['balance']
            init_balance_accounts[account.id] =  \
                accounts_by_ids[account.id].get('init_balance', 0.0)

            # if any amount is != 0 in comparisons, we have to display the
            # whole account
            display_account = False
            comp_accounts = []
            for comp_account_by_id in comp_accounts_by_ids:
                values = comp_account_by_id.get(account.id)
                values.update(
                    self._get_diff(balance_accounts[account.id], values['balance']))
                display_account = any((values.get('credit', 0.0),
                                       values.get('debit', 0.0),
                                       values.get('balance', 0.0),
                                       values.get('init_balance', 0.0)))
                comp_accounts.append(values)
            comparisons_accounts[account.id] = comp_accounts
            # we have to display the account if a comparison as an amount or
            # if we have an amount in the main column
            # we set it as a property to let the data in the report if someone
            # want to use it in a custom report
            display_account = display_account\
                or any((debit_accounts[account.id],
                        credit_accounts[account.id],
                        balance_accounts[account.id],
                        init_balance_accounts[account.id]))
            to_display_accounts.update(
                {account.id: display_account and
                 to_display_accounts[account.id]})

        context_report_values = {
            'fiscalyear': fiscalyear,
            'start_date': start_date,
            'stop_date': stop_date,
            'start_period': start_period,
            'stop_period': stop_period,
            'chart_account': chart_account,
            'comparison_mode': comparison_mode,
            'nb_comparison': nb_comparisons,
            'initial_balance': init_balance,
            'initial_balance_mode': initial_balance_mode,
            'comp_params': comparison_params,
            'to_display_accounts': to_display_accounts,
            'init_balance_accounts': init_balance_accounts,
            'comparisons_accounts': comparisons_accounts,
            'debit_accounts': debit_accounts,
            'credit_accounts': credit_accounts,
            'balance_accounts': balance_accounts,
        }

        return objects, new_ids, context_report_values
