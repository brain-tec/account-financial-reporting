# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
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

from openerp.osv import orm
from lxml import etree
from openerp.osv.orm import setup_modifiers

class AccountErDetailWizard(orm.TransientModel):
    """Will launch trial balance report and pass required args"""

    _inherit = "account.common.balance.report"
    _name = "er.detail.webkit"
    _description = "ER Detail Report"

    def _print_report(self, cursor, uid, ids, data, context=None):
        context = context or {}
        # we update form with display account value
        data = self.pre_print_report(cursor, uid, ids, data, context=context)
        return {'type': 'ir.actions.report.xml',
                'report_name': 'account.account_report_er_detail_webkit',
                'datas': data}

    def onchange_filter(self, cr, uid, ids, filter='filter_no',
                        fiscalyear_id=False, context=None):
        if filter not in ('filter_date', 'filter_period'):
            return {'warning': {'title': 'Error!', 'message': 'This value cannot be selected.'}, 'value': {'filter': False}}
        else:
            return super(AccountErDetailWizard, self).onchange_filter(cr, uid, ids, filter=filter, fiscalyear_id=fiscalyear_id,context=context)
