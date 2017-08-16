## -*- coding: utf-8 -*-
<!DOCTYPE html SYSTEM "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <style type="text/css">
            .account_level_1 {
                text-transform: uppercase;
                font-size: 15px;
                background-color:#F0F0F0;
            }

            .account_level_2 {
                font-size: 12px;
                background-color:#F0F0F0;
            }

            .regular_account_type {
                font-weight: normal;
            }

            .view_account_type {
                font-weight: bold;
            }

            .account_level_consol {
                font-weight: normal;
            	font-style: italic;
            }

            ${css}

            .list_table .act_as_row {
                margin-top: 10px;
                margin-bottom: 10px;
                font-size:10px;
            }
        </style>
    </head>
    <body>
        <%!
        def amount(text):
            return text.replace('-', '&#8209;')  # replace by a non-breaking hyphen (it will not word-wrap between hyphen and numbers)
        %>

        <%setLang(user.lang)%>

        <%
        initial_balance_text = {'initial_balance': _('Computed'), 'opening_balance': _('Opening Entries'), False: _('No')}
        %>

        <div class="act_as_table data_table">
            <div class="act_as_row labels">
                <div class="act_as_cell">${_('Chart of Account')}</div>
                <div class="act_as_cell">${_('Fiscal Year')}</div>
                <div class="act_as_cell">
                    %if filter_form(data) == 'filter_date':
                        ${_('Dates Filter')}
                    %else:
                        ${_('Periods Filter')}
                    %endif
                </div>
                <div class="act_as_cell">${_('Accounts Filter')}</div>
                <div class="act_as_cell">${_('Target Moves')}</div>
                <div class="act_as_cell">${_('Initial Balance')}</div>
            </div>
            <div class="act_as_row">
                <div class="act_as_cell">${ chart_account.name }</div>
                <div class="act_as_cell">${ fiscalyear.name if fiscalyear else '-' }</div>
                <div class="act_as_cell">
                    ${_('From:')}
                    %if filter_form(data) == 'filter_date':
                        ${formatLang(start_date, date=True) if start_date else u'' }
                    %else:
                        ${start_period.name if start_period else u''}
                    %endif
                    ${_('To:')}
                    %if filter_form(data) == 'filter_date':
                        ${ formatLang(stop_date, date=True) if stop_date else u'' }
                    %else:
                        ${stop_period.name if stop_period else u'' }
                    %endif
                </div>
                <div class="act_as_cell">
                    %if accounts(data):
                        ${', '.join([account.code for account in accounts(data)])}
                    %else:
                        ${_('All')}
                    %endif
                </div>
                <div class="act_as_cell">${ display_target_move(data) }</div>
                <div class="act_as_cell">${ initial_balance_text[initial_balance_mode] }</div>
            </div>
        </div>

        %for index, params in enumerate(comp_params):
            <div class="act_as_table data_table">
                <div class="act_as_row">
                    <div class="act_as_cell">${_('Comparison %s') % (index + 1,)} (${"C%s" % (index + 1,)})</div>
                    <div class="act_as_cell">
                        %if params['comparison_filter'] == 'filter_date':
                            ${_('Dates Filter:')}&nbsp;${formatLang(params['start'], date=True) }&nbsp;-&nbsp;${formatLang(params['stop'], date=True) }
                        %elif params['comparison_filter'] == 'filter_period':
                            ${_('Periods Filter:')}&nbsp;${params['start'].name}&nbsp;-&nbsp;${params['stop'].name}
                        %else:
                            ${_('Fiscal Year :')}&nbsp;${params['fiscalyear'].name}
                        %endif
                    </div>
                    <div class="act_as_cell">${_('Initial Balance:')} ${ initial_balance_text[params['initial_balance_mode']] }</div>
                </div>
            </div>
        %endfor

        <div class="act_as_table data_table" style="margin-top: 20px;">
            <div class="act_as_thead">
                <div class="act_as_row labels">
                    ## code
                    <div class="act_as_cell first_column" style="width: 20px;"></div>
                    ## account name
                    <div class="act_as_cell" style="width: 80px;"></div>
                    ## c_rechnung_actual_year
                    <div class="act_as_cell amount" style="width: 40px; text-align: center;">${_('Berichtsjahr')}</div>
                    ## d_rechnung_actual_year_percent
                    <div class="act_as_cell amount" style="width: 40px; text-align: center">${_('Budget')}</div>
                    ## g_rechnung_previous_year
                    <div class="act_as_cell amount" style="width: 40px; text-align: center">${_('Vorjahr')}</div>
                    ## i_forecast_previous_quarter
                    <div class="act_as_cell amount" style="width: 40px; text-align: center">${_('Vorquartal')}</div>
                </div>
            </div>
        </div>
        <div class="act_as_table list_table">
            <div class="act_as_thead">
                <div class="act_as_row labels">
                    ## code
                    <div class="act_as_cell first_column" style="width: 20px;">${_('Code')}</div>
                    ## account name
                    <div class="act_as_cell" style="width: 80px;">${_('Account')}</div>
                    ## c_rechnung_actual_year
                    <div class="act_as_cell amount" style="width: 20px;">${_('Betrag')}</div>
                    ## d_rechnung_actual_year_percent
                    <div class="act_as_cell amount" style="width: 20px;">${_('%')}</div>
                    ## e_budget_actual_year
                    <div class="act_as_cell amount" style="width: 20px;">${_('Betrag')}</div>
                    ## f_rechung_budget_actual_year_diff
                    <div class="act_as_cell amount" style="width: 20px;">${_('Abw. CHF')}</div>
                    ## g_rechnung_previous_year
                    <div class="act_as_cell amount" style="width: 20px;">${_('Betrag')}</div>
                    ## h_rechnung_previous_actual_year_diff
                    <div class="act_as_cell amount" style="width: 20px;">${_('Abw. CHF')}</div>
                    ## i_forecast_previous_quarter
                    <div class="act_as_cell amount" style="width: 20px;">${_('Betrag')}</div>
                    ## j_forecast_previous_quarter_actual_year_diff
                    <div class="act_as_cell amount" style="width: 20px;">${_('Abw. CHF')}</div>
##                     %if comparison_mode == 'no_comparison':
##                         %if initial_balance_mode:
##                             ## initial balance
##                             <div class="act_as_cell amount" style="width: 30px;">${_('Initial Balance')}</div>
##                         %endif
##                         ## debit
##                         <div class="act_as_cell amount" style="width: 30px;">${_('Debit')}</div>
##                         ## credit
##                         <div class="act_as_cell amount" style="width: 30px;">${_('Credit')}</div>
##                     %endif
                    ## balance
##                     <div class="act_as_cell amount" style="width: 30px;">
##                     %if comparison_mode == 'no_comparison' or not fiscalyear:
##                         ${_('Balance')}
##                     %else:
##                         ${_('Balance %s') % (fiscalyear.name,)}
##                     %endif
##                     </div>
##                     %if comparison_mode in ('single', 'multiple'):
##                         %for index in range(nb_comparison):
##                             <div class="act_as_cell amount" style="width: 30px;">
##                                 %if comp_params[index]['comparison_filter'] == 'filter_year' and comp_params[index].get('fiscalyear', False):
##                                     ${_('Balance %s') % (comp_params[index]['fiscalyear'].name,)}
##                                 %else:
##                                     ${_('Balance C%s') % (index + 1,)}
##                                 %endif
##                             </div>
##                             %if comparison_mode == 'single':  ## no diff in multiple comparisons because it shows too data
##                                 <div class="act_as_cell amount" style="width: 30px;">${_('Difference')}</div>
##                                 <div class="act_as_cell amount" style="width: 30px;">${_('% Difference')}</div>
##                             %endif
##                         %endfor
##                     %endif
                </div>
            </div>

            <div class="act_as_tbody">
                <%
                last_child_consol_ids = []
                last_level = False
                %>
##                 %for current_account in objects:
##                     <%
##                     print '<------'
##                     print current_account.code
##                     print current_account.level
##                     print '------>'
##                     %>
##                 %endfor
                %for current_account in lines:
                    <%
## ##                     print current_account
## ##                     print current_account['account_id']
## ##                     print current_account['account_type']
##                     print "%s_account_type" % (current_account['account_type'], )
                    if current_account['account_id']:
                        if not to_display_accounts[current_account['account_id']]:
                            continue

                        comparisons = comparisons_accounts[current_account['account_id']]

                    if not current_account['account_id']:
                        level = last_level
                        level = current_account['level'] or 0
                        level_class = "account_level_%s" % (level,)
                    elif current_account['account_id'] in last_child_consol_ids:
                        # current account is a consolidation child of the last account: use the level of last account
                        level = last_level
                        level_class = "account_level_consol"
                    else:
                        # current account is a not a consolidation child: use its own level
                        level = current_account['level'] or 0
                        level_class = "account_level_%s" % (level,)
                        last_child_consol_ids = [child_consol_id.id for child_consol_id in current_account['child_consol_ids']]
                        last_level = current_account['level']
                    print current_account['code']
                    print level_class
                    %>
                    <div class="act_as_row lines ${level_class} ${"%s_account_type" % (current_account['account_type'],)}">
                        ## code
                        <div class="act_as_cell first_column">${current_account['code']}</div>
                        ## account name
                        <div class="act_as_cell" style="padding-left: ${level * 5}px;">${current_account['name']}</div>
                        ## c_rechnung_actual_year
                        <%
                        c_rechnung_actual_year_value = 0
                        if not current_account['values_need_to_be_updated']:
                            c_rechnung_actual_year_value = balance_accounts[current_account['account_id']]
                        else:
                            c_rechnung_actual_year_value = current_account['c_rechnung_actual_year']
                        %>
                        <div class="act_as_cell amount">${formatLang(c_rechnung_actual_year_value) | amount}</div>
                        ## d_rechnung_actual_year_percent
                        <div class="act_as_cell amount">
                        %if not current_account['account_id'] or balance_accounts_percent[current_account['account_id']] is False:
                           ${round(c_rechnung_actual_year_value / amount_betriebsertrag * 100,1) | amount} &#37;
                        %else:
                           ${round(balance_accounts_percent[current_account['account_id']],1) | amount} &#37;
                        %endif
                        </div>
                        ## e_budget_actual_year
                        <%
                        e_budget_actual_year = 0
                        if not current_account['values_need_to_be_updated']:
                            e_budget_actual_year = budget_accounts[current_account['account_id']]
                        else:
                            e_budget_actual_year = current_account['e_budget_actual_year']
                        %>
                        <div class="act_as_cell amount">${formatLang(e_budget_actual_year) | amount}</div>
                        ## f_rechung_budget_actual_year_diff
                        <div class="act_as_cell amount">${formatLang(c_rechnung_actual_year_value - e_budget_actual_year) | amount}</div>
                        ## g_rechnung_previous_year
                        %if current_account['account_id']:
                            %if comparison_mode in ('single', 'multiple'):
                                %for comp_account in comparisons:
                                    <%
                                        g_rechnung_previous_year = comp_account['balance']
                                    %>
                                    <div class="act_as_cell amount">${formatLang(g_rechnung_previous_year) | amount}</div>
##                                     %if comparison_mode == 'single':  ## no diff in multiple comparisons because it shows too data
##                                         <div class="act_as_cell amount">${formatLang(comp_account['diff']) | amount}</div>
##                                         <div class="act_as_cell amount">
##                                         %if comp_account['percent_diff'] is False:
##                                          ${ '-' }
##                                         %else:
##                                            ${int(round(comp_account['percent_diff'])) | amount} &#37;
##                                         %endif
##                                         </div>
##                                     %endif
                                %endfor
                            %endif
                        %else:
                            <div class="act_as_cell amount">${formatLang(current_account['g_rechnung_previous_year']) | amount}</div>
                        %endif
                        ## h_rechnung_previous_actual_year_diff
                        <div class="act_as_cell amount">${formatLang(c_rechnung_actual_year_value - g_rechnung_previous_year) | amount}</div>
                        ## i_forecast_previous_quarter
                        <%
                        i_forecast_previous_quarter= 0
                        if current_account['account_id']:
                            i_forecast_previous_quarter = balance_forecast_accounts[current_account['account_id']]
                        else:

                            i_forecast_previous_quarter = current_account['i_forecast_previous_quarter']
                        %>
                        <div class="act_as_cell amount">${formatLang(i_forecast_previous_quarter) | amount}</div>
                        ## j_forecast_previous_quarter_actual_year_diff
                        <div class="act_as_cell amount">${formatLang(c_rechnung_actual_year_value - i_forecast_previous_quarter) | amount}</div>



##                         %if comparison_mode == 'no_comparison':
##                             %if initial_balance_mode and current_account['account_id']:
##                                 ## opening balance
##                                 <div class="act_as_cell amount">${formatLang(init_balance_accounts[current_account['account_id']]) | amount}</div>
##                             %endif
##                             ## debit
##                             %if current_account['account_id']:
##                                 <div class="act_as_cell amount">${formatLang(debit_accounts[current_account['account_id']]) | amount}</div>
##                                 ## credit
##                                 <div class="act_as_cell amount">${formatLang(credit_accounts[current_account['account_id']]) | amount}</div>
##                             %endif
##                         %endif
##                         ## balance
##                         %if current_account['account_id']:
##                             <div class="act_as_cell amount">${formatLang(balance_accounts[current_account['account_id']]) | amount}</div>
##                         %else:
##                             <div class="act_as_cell amount">${formatLang(current_account['balance']) | amount}</div>
##                         %endif
##                         %if comparison_mode in ('single', 'multiple'):
##                             %for comp_account in comparisons:
##                                 <div class="act_as_cell amount">${formatLang(comp_account['balance']) | amount}</div>
##                                 %if comparison_mode == 'single':  ## no diff in multiple comparisons because it shows too data
##                                     <div class="act_as_cell amount">${formatLang(comp_account['diff']) | amount}</div>
##                                     <div class="act_as_cell amount">
##                                     %if comp_account['percent_diff'] is False:
##                                      ${ '-' }
##                                     %else:
##                                        ${int(round(comp_account['percent_diff'])) | amount} &#37;
##                                     %endif
##                                     </div>
##                                 %endif
##                             %endfor
##                         %endif
                    </div>
                %endfor
            </div>
        </div>
    </body>
</html>
