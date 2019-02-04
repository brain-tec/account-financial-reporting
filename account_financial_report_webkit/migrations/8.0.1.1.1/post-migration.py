# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi.
#    Copyright Camptocamp SA 2011
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from logging import getLogger
_logger = getLogger(__name__)

def migrate(cr, version):
    """

    :param cr:
    :param version:
    :return:
    """
    _logger.debug("fetching records..")
    cr.execute("""
    SELECT
    x.id, ail.id, x.move_id, ai.id, sequence, 
    product_id_category_inv_sequence, product_id_sequence_for_invoice
    FROM
    public.account_move_line
    x
    join
    account_move
    am
    on
    am.id = x.move_id
    join
    account_invoice
    ai
    on
    am.id = ai.move_id
    join
    account_invoice_line
    ail
    on
    ail.invoice_id = ai.id
    """)
    data = cr.fetchall()
    if not data:
        return

    moves={}

    invoices={}
    result = {}
    _logger.debug("compting invoices and moves")
    for aml_id, ail_id, move_id, inv_id , seq, product_id_category_inv_sequence,product_id_sequence_for_invoice in data:
        lines_move = moves.setdefault(move_id,set([]))
        lines_move.add((aml_id,move_id))

        lines_inv = invoices.setdefault(inv_id,set([]))
        lines_inv.add((ail_id,move_id,inv_id, (seq,
        product_id_category_inv_sequence,product_id_sequence_for_invoice,
        ail_id) ))

    _logger.debug("computing invoiceline moveline relation")
    for inv_id, data in invoices.iteritems():
        data = sorted(list(data),key=lambda r: r[3])
        move_data = sorted(list(moves[data[0][1]]),key=lambda r:r[0],
        reverse=True)
        move_len = len(move_data)
        for i in xrange(len(data)):
            if i < move_len:
                result[move_data[move_len-1-i][0]] = data[i][0]

    result =result.items()
    for i in xrange(0, len(result), 1000):
        _logger.debug("updating db %s",i)
        upd_str = ','.join(map(str,result[i:i+1000]))

        cr.execute("""
    update
    account_move_line as ail
    set
    invoice_line_id = c.inv_id
    from
    (
        values {upd_str}
    ) as c(id, inv_id)
    where
    c.id = ail.id
    """.format(upd_str=upd_str))