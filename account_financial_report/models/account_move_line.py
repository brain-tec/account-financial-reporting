# Copyright 2019 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    counterpart_account_id = fields.Many2one('account.account', compute='_compute_counteraccounts',
         store=True)

    @api.depends('journal_id', 'line_ids','line_ids.account_id','line_ids.debit','line_ids.credit', 'journal_id.default_debit_account_id', 'journal_id.default_credit_account_id')
    def _compute_counteraccounts(self):
        for move in self:
            value = False
            # If move has an invoice, return invoice's account_id
            payment_term_lines = move.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
            if payment_term_lines:
                move.counterpart_account_id = payment_term_lines[0].account_id
            continue
            # If move belongs to a bank journal, return the journal's account (debit/credit should normally be the same)
            if move.journal_id.type == 'bank' and move.journal_id.default_debit_account_id:
                move.counterpart_account_id = move.journal_id.default_debit_account_id
                continue
            # If the move is an automatic exchange rate entry, take the gain/loss account set on the exchange journal
            elif move.journal_id.type == 'general' and move.journal_id == self.env.company.currency_exchange_journal_id:
                accounts = [
                    move.journal_id.default_debit_account_id,
                    move.journal_id.default_credit_account_id,
                ]
                lines = move.line_ids.filtered(lambda r: r.account_id in accounts)
                if len(lines) == 1:
                    move.counterpart_account_id = lines.account_id
                    continue

            # Look for an account used a single time in the move, that has no originator tax
            aml_debit = self.env['account.move.line']
            aml_credit = self.env['account.move.line']
            for aml in move.line_ids:
                if aml.debit > 0:
                    aml_debit += aml
                if aml.credit > 0:
                    aml_credit += aml
            if len(aml_debit) == 1:
                value = aml_debit[0].account_id
            elif len(aml_credit) == 1:
                value = aml_credit[0].account_id
            else:
                aml_debit_wo_tax = [a for a in aml_debit if not a.tax_line_id]
                aml_credit_wo_tax = [a for a in aml_credit if not a.tax_line_id]
                if len(aml_debit_wo_tax) == 1:
                    value = aml_debit_wo_tax[0].account_id
                elif len(aml_credit_wo_tax) == 1:
                    value = aml_credit_wo_tax[0].account_id
            move.counterpart_account_id = value





class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    counterpart_account_id = fields.Many2one('account.account','Counter Account', related="move_id.counterpart_account_id")

    @api.model_cr
    def init(self):
        """
            The join between accounts_partners subquery and account_move_line
            can be heavy to compute on big databases.
            Join sample:
                JOIN
                    account_move_line ml
                        ON ap.account_id = ml.account_id
                        AND ml.date < '2018-12-30'
                        AND ap.partner_id = ml.partner_id
                        AND ap.include_initial_balance = TRUE
            By adding the following index, performances are strongly increased.
        :return:
        """
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = '
                         '%s',
                         ('account_move_line_account_id_partner_id_index',))
        if not self._cr.fetchone():
            self._cr.execute("""
            CREATE INDEX account_move_line_account_id_partner_id_index
            ON account_move_line (account_id, partner_id)""")
