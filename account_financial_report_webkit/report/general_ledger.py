# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi, Guewen Baconnier
#    Copyright Camptocamp SA 2011
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

from operator import itemgetter
from itertools import groupby
from datetime import datetime

from openerp.report import report_sxw
from openerp import pooler
from openerp.tools.translate import _
from .common_reports import CommonReportHeaderWebkit
from .webkit_parser_header_fix import HeaderFooterTextWebKitParser


class GeneralLedgerWebkit(report_sxw.rml_parse, CommonReportHeaderWebkit):

    def __init__(self, cursor, uid, name, context):
        super(GeneralLedgerWebkit, self).__init__(
            cursor, uid, name, context=context)
        self.pool = pooler.get_pool(self.cr.dbname)
        self.cursor = self.cr

        company = self.pool.get('res.users').browse(
            self.cr, uid, uid, context=context).company_id
        header_report_name = ' - '.join(
            (_('GENERAL LEDGER'), company.name, company.currency_id.name))

        footer_date_time = self.formatLang(
            str(datetime.today()), date_time=True)

        self.localcontext.update({
            'cr': cursor,
            'uid': uid,
            'report_name': _('General Ledger'),
            'display_account': self._get_display_account,
            'display_account_raw': self._get_display_account_raw,
            'filter_form': self._get_filter,
            'target_move': self._get_target_move,
            'initial_balance': self._get_initial_balance,
            'amount_currency': self._get_amount_currency,
            'display_target_move': self._get_display_target_move,
            'accounts': self._get_accounts_br,
            'additional_args': [
                ('--header-font-name', 'Helvetica'),
                ('--footer-font-name', 'Helvetica'),
                ('--header-font-size', '10'),
                ('--footer-font-size', '6'),
                ('--header-left', header_report_name),
                ('--header-spacing', '2'),
                ('--footer-left', footer_date_time),
                ('--footer-right',
                 ' '.join((_('Page'), '[page]', _('of'), '[topage]'))),
                ('--footer-line',),
            ],
        })

    def set_context(self, objects, data, ids, report_type=None):
        """Populate a ledger_lines attribute on each browse record that will be
        used by mako template"""
        new_ids = data['form']['account_ids'] or data[
            'form']['chart_account_id']

        # Account initial balance memoizer
        init_balance_memoizer = {}

        # Reading form
        main_filter = self._get_form_param('filter', data, default='filter_no')
        target_move = self._get_form_param('target_move', data, default='all')
        start_date = self._get_form_param('date_from', data)
        stop_date = self._get_form_param('date_to', data)
        do_centralize = self._get_form_param('centralize', data)
        remove_zero_lines = self._get_form_param('remove_null_lines', data)
        start_period = self.get_start_period_br(data)
        stop_period = self.get_end_period_br(data)
        fiscalyear = self.get_fiscalyear_br(data)
        chart_account = self._get_chart_account_id_br(data)

        self.localcontext.update({'remove_zero_lines': remove_zero_lines, })

        if main_filter == 'filter_no':
            start_period = self.get_first_fiscalyear_period(fiscalyear)
            stop_period = self.get_last_fiscalyear_period(fiscalyear)

        # computation of ledger lines
        if main_filter == 'filter_date':
            start = start_date
            stop = stop_date
        else:
            start = start_period
            stop = stop_period

        initial_balance = self.is_initial_balance_enabled(main_filter)
        initial_balance_mode = initial_balance \
            and self._get_initial_balance_mode(start) or False

        # Retrieving accounts
        accounts = self.get_all_accounts(new_ids, exclude_type=['view'])
        if initial_balance_mode == 'initial_balance':
            init_balance_memoizer = self._compute_initial_balances(
                accounts, start, fiscalyear)
        elif initial_balance_mode == 'opening_balance':
            init_balance_memoizer = self._read_opening_balance(accounts, start)

        ledger_lines_memoizer = self._compute_account_ledger_lines(
            accounts, init_balance_memoizer, main_filter, target_move, start,
            stop)
        objects = self.pool.get('account.account').browse(
            self.cursor,
            self.uid,
            accounts,
            context=self.localcontext)

        init_balance = {}
        ledger_lines = {}
        budgets = {}

        ### HACK by BT-mgerecke
        # If a period is given, get the earliest and latest dates.
        if main_filter != 'filter_date':
            date_lower = start.date_start
            date_upper = stop.date_stop
        else:
            date_lower = start
            date_upper = stop
        ### End HACK

        date_format = "%Y-%m-%d"
        for account in objects:
            if do_centralize and account.centralized \
                    and ledger_lines_memoizer.get(account.id):
                ledger_lines[account.id] = self._centralize_lines(
                    main_filter, ledger_lines_memoizer.get(account.id, []))
            else:
                ledger_lines[account.id] = ledger_lines_memoizer.get(
                    account.id, [])
            init_balance[account.id] = init_balance_memoizer.get(account.id, {})
            ### HACK by BT-mgerecke
            # Budgets are monthly but may be any timespan.
            # Attention! For Valaiscom the account code is stored in column name not in column code.
            # Get first and maybe partly budget of periode
            self.cr.execute("SELECT planned_amount,date_from,date_to,id FROM crossovered_budget_lines"
                            " WHERE general_budget_id IN (SELECT id FROM account_budget_post WHERE name = %s)"
                            " AND (to_date(%s,'yyyy-mm-dd') between date_from AND date_to)",
                            (account['code'], date_lower, ))
            bgt_first = self.cr.fetchone()

            # Get sum of all intermediate and complete budgets
            self.cr.execute("SELECT SUM(planned_amount) FROM crossovered_budget_lines"
                            " WHERE general_budget_id IN (SELECT id FROM account_budget_post WHERE name = %s)"
                            " AND date_from > to_date(%s,'yyyy-mm-dd') AND date_to < to_date(%s,'yyyy-mm-dd')",
                            (account['code'], date_lower, date_upper, ))
            bgt_inter = self.cr.fetchone()
            if isinstance(bgt_inter, tuple):
                bgt_inter = bgt_inter[0]

            # Get last and maybe partly budget of periode
            self.cr.execute("SELECT planned_amount,date_from,date_to,id FROM crossovered_budget_lines"
                            " WHERE general_budget_id IN (SELECT id FROM account_budget_post WHERE name = %s)"
                            " AND (to_date(%s,'yyyy-mm-dd') between date_from AND date_to)",
                            (account['code'], date_upper, ))
            bgt_last = self.cr.fetchone()

            # Jump to next iteration if no budget was found.
            if (not bgt_first) and (not bgt_inter) and (not bgt_last):
                budgets[account.id] = None
                continue

            # Get budget from first/last budget if it was found
            if bgt_first:
                datetime_bgt_f_lower = datetime.strptime(bgt_first[1], date_format)
                datetime_bgt_f_upper = datetime.strptime(bgt_first[2], date_format)
                bgt_f_days = (datetime_bgt_f_upper - datetime_bgt_f_lower).days + 1.0

            if bgt_last:
                datetime_bgt_l_lower = datetime.strptime(bgt_last[1], date_format)
                datetime_bgt_l_upper = datetime.strptime(bgt_last[2], date_format)
                bgt_l_days = (datetime_bgt_l_upper - datetime_bgt_l_lower).days + 1.0

            # Check if budget ids are identical, this indicates that selected period only touches one single budget.
            bgt_first_part = 0.0
            bgt_last_part = 0.0
            if bgt_first and bgt_last:
                datetime_lower = datetime.strptime(date_lower, date_format)
                datetime_upper = datetime.strptime(date_upper, date_format)
                if bgt_first[3] == bgt_last[3]:
                    bgt_first_part = (datetime_upper - datetime_lower).days / bgt_f_days
                else:
                    bgt_first_part = (datetime_lower - datetime_bgt_f_lower).days / bgt_f_days
                    bgt_last_part = (datetime_bgt_l_upper - datetime_upper).days / bgt_l_days

            sum_budget = 0.0
            if bgt_first:
                sum_budget += bgt_first[0] * bgt_first_part
            if bgt_inter:
                sum_budget += bgt_inter
            if bgt_last:
                sum_budget += bgt_last[0] * bgt_last_part

            if account.negative_notation:
                budgets[account.id] = -1.0 * sum_budget
            else:
                budgets[account.id] = sum_budget
            ### End HACK

        self.localcontext.update({
            'fiscalyear': fiscalyear,
            'start_date': start_date,
            'stop_date': stop_date,
            'start_period': start_period,
            'stop_period': stop_period,
            'chart_account': chart_account,
            'budget': budgets,
            'initial_balance_mode': initial_balance_mode,
            'init_balance': init_balance,
            'ledger_lines': ledger_lines,
        })

        return super(GeneralLedgerWebkit, self).set_context(
            objects, data, new_ids, report_type=report_type)

    def _centralize_lines(self, filter, ledger_lines, context=None):
        """ Group by period in filter mode 'period' or on one line in filter
            mode 'date' ledger_lines parameter is a list of dict built
            by _get_ledger_lines"""
        def group_lines(lines):
            if not lines:
                return {}
            sums = reduce(lambda line, memo:
                          dict((key, value + memo[key]) for key, value
                               in line.iteritems() if key in
                               ('balance', 'debit', 'credit')), lines)

            res_lines = {
                'balance': sums['balance'],
                'debit': sums['debit'],
                'credit': sums['credit'],
                'lname': _('Centralized Entries'),
                'account_id': lines[0]['account_id'],
            }
            return res_lines

        centralized_lines = []
        if filter == 'filter_date':
            # by date we centralize all entries in only one line
            centralized_lines.append(group_lines(ledger_lines))

        else:  # by period
            # by period we centralize all entries in one line per period
            period_obj = self.pool.get('account.period')
            # we need to sort the lines per period in order to use groupby
            # unique ids of each used period id in lines
            period_ids = list(
                set([line['lperiod_id'] for line in ledger_lines]))
            # search on account.period in order to sort them by date_start
            sorted_period_ids = period_obj.search(
                self.cr, self.uid, [('id', 'in', period_ids)],
                order='special desc, date_start', context=context)
            sorted_ledger_lines = sorted(
                ledger_lines, key=lambda x: sorted_period_ids.
                index(x['lperiod_id']))

            for period_id, lines_per_period_iterator in groupby(
                    sorted_ledger_lines, itemgetter('lperiod_id')):
                lines_per_period = list(lines_per_period_iterator)
                if not lines_per_period:
                    continue
                group_per_period = group_lines(lines_per_period)
                group_per_period.update({
                    'lperiod_id': period_id,
                    # period code is anyway the same on each line per period
                    'period_code': lines_per_period[0]['period_code'],
                })
                centralized_lines.append(group_per_period)

        return centralized_lines

    def _compute_account_ledger_lines(self, accounts_ids,
                                      init_balance_memoizer, main_filter,
                                      target_move, start, stop):
        res = {}
        for acc_id in accounts_ids:
            move_line_ids = self.get_move_lines_ids(
                acc_id, main_filter, start, stop, target_move)
            if not move_line_ids:
                res[acc_id] = []
                continue

            lines = self._get_ledger_lines(move_line_ids, acc_id)
            res[acc_id] = lines
        return res

    def _get_ledger_lines(self, move_line_ids, account_id):

        remove_zero_lines = self.localcontext.get('remove_zero_lines', False)

        if not move_line_ids:
            return []
        res = self._get_move_line_datas(move_line_ids)
        # computing counter part is really heavy in term of ressouces
        # consuption looking for a king of SQL to help me improve it
        move_ids = [x.get('move_id') for x in res]
        counter_parts = self._get_moves_counterparts(move_ids, account_id)
        for line in res:
            line['counterparts'] = counter_parts.get(line.get('move_id'), '')

        if remove_zero_lines:
            new_res = []
            for line in res:
                debit = line.get('debit', 0.0)
                credit = line.get('credit', 0.0)

                if debit != 0.0 or credit != 0.0:
                    new_res.append(line)

            return new_res
        else:
            return res

HeaderFooterTextWebKitParser(
    'report.account.account_report_general_ledger_webkit',
    'account.account',
    'addons/account_financial_report_webkit/report/templates/\
                                        account_report_general_ledger.mako',
    parser=GeneralLedgerWebkit)
