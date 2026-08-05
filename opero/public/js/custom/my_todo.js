// Opero: client scripts for My ToDo
// Migrated from Frappe Cloud Client Scripts (enabled Form scripts).

// --- ToDo List ---
function strip_html(html) {
    const temp = document.createElement("div");
    temp.innerHTML = html;
    return temp.textContent || temp.innerText || "";
}

frappe.ui.form.on('My ToDo', {
    onload: function (frm) {
        render_todo_dashboard(frm);
    },
    refresh: function (frm) {
        render_todo_dashboard(frm);
    }
});

function render_todo_dashboard(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'ToDo',
            filters: {
                allocated_to: frappe.session.user,
                status: ['!=', 'Closed']
            },
            fields: ['name', 'custom_title', 'description', 'status', 'priority', 'reference_type', 'reference_name', 'date'],
            order_by: 'date asc',
            limit_page_length: 500
        },
        callback: function (r) {
            const wrapper = frm.fields_dict.todo_html.$wrapper;
            wrapper.empty();

            // Header
            const header = `
              <div style="margin-bottom:16px;display:flex;gap:8px;align-items:center;justify-content:space-between;">
                <div>
                  <button class="btn btn-primary btn-sm" id="create-todo-btn">➕ New ToDo</button>
                </div>
                <div style="display:flex; gap:6px; align-items:center;">
                  <input id="todo-search" type="text" placeholder="Search ToDos…" 
                         style="height:26px; padding:3px 8px; border:1px solid #e5e5e5; border-radius:6px; width:220px;">
                  <button class="btn btn-default btn-xs" id="expand-all">Expand all</button>
                  <button class="btn btn-default btn-xs" id="collapse-all">Collapse all</button>
                </div>
              </div>
            `;

            // Sort: earliest first, undated last
            const rows = (r.message || []).sort((a,b) => {
                const ad = a.date ? new Date(a.date) : null;
                const bd = b.date ? new Date(b.date) : null;
                if (ad && bd) return ad - bd;
                if (ad && !bd) return -1;
                if (!ad && bd) return 1;
                return 0;
            });

            // Group (robust against timezone/format)
            const groups = { overdue: [], today: [], upcoming: [], no_due: [] };
            
            // Use Frappe's today in YYYY-MM-DD, then parse with moment
            const today = moment(frappe.datetime.get_today(), 'YYYY-MM-DD');
            
            rows.forEach(todo => {
                if (!todo.date) { groups.no_due.push(todo); return; }
            
                // Ensure we parse server date string explicitly
                const due = moment(todo.date, 'YYYY-MM-DD');
            
                if (due.isBefore(today, 'day')) groups.overdue.push(todo);
                else if (due.isSame(today, 'day')) groups.today.push(todo);
                else groups.upcoming.push(todo);
            });

            // Card renderer
            function renderCard(todo, dueClass = '') {
                const title = strip_html(todo.custom_title || 'Untitled Task');
                const description = strip_html(todo.description || '');
                const truncated = description.length > 100 ? description.substring(0, 100) + '...' : description;

                const dueLine = todo.date
                    ? `<br><small class="${dueClass}">Due: ${frappe.datetime.str_to_user(todo.date)}</small>`
                    : '';

                const refLine = (todo.reference_type && todo.reference_name)
                    ? `<br><small>Ref: ${todo.reference_type} ${todo.reference_name}</small>`
                    : '';

                return `
                    <div class="todo-card" style="margin-bottom:10px;padding:10px;border:1px solid #ddd;border-radius:6px;">
                        <div>
                            <b><a href="/app/todo/${todo.name}" target="_blank" style="text-decoration:none;">
                                ${frappe.utils.escape_html(title)}
                            </a></b><br>
                            <small>${frappe.utils.escape_html(truncated)}</small><br>
                            <small>Status: ${todo.status} | Priority: ${todo.priority}</small>
                            ${dueLine}
                            ${refLine}
                        </div>
                        <div style="display:flex;justify-content:flex-end;margin-top:8px;">
                            <button class="btn btn-sm btn-outline-danger close-todo" data-name="${todo.name}">Close</button>
                        </div>
                    </div>
                `;
            }

            // Section renderer
            function section(title, arr, dueClass = '', openByDefault = false) {
                if (!arr.length) return '';
                const cards = arr.map(t => renderCard(t, dueClass)).join('');
                return `
                    <details class="todo-section" ${openByDefault ? 'open' : ''} style="margin-bottom:10px;">
                        <summary style="cursor:pointer; user-select:none; padding:6px 8px; border:1px solid #e5e5e5; border-radius:6px; background:#fafafa; display:flex; align-items:center; justify-content:space-between;">
                            <span>${title}</span>
                            <span style="opacity:.7; font-size:12px;">${arr.length}</span>
                        </summary>
                        <div style="margin-top:8px;">${cards}</div>
                    </details>
                `;
            }

            // Build UI
            const body = rows.length
                ? section('Overdue', groups.overdue, 'text-danger', false)
                + section('Due Today', groups.today, 'text-warning', false)
                + section('Upcoming', groups.upcoming, '', false)
                + section('No Due Date', groups.no_due, 'text-muted', false)
                : '<p>No open ToDos assigned to you.</p>';

            // Render open baskets + a placeholder for closed basket
            wrapper.html(header + body + `<div id="closed-basket"></div>`);
            
            // Debounce helper
            function debounce(fn, ms) {
              let t; 
              return function(...args) { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), ms); };
            }
            
            // Apply filter
            function applyTodoFilter(term) {
              const q = (term || '').trim().toLowerCase();
            
              // Expand all when searching
              if (q) wrapper.find('details.todo-section').attr('open', true);
            
              // Filter cards
              const sections = wrapper.find('details.todo-section');
              sections.each(function() {
                const section = $(this);
                let visibleCount = 0;
            
                section.find('.todo-card').each(function() {
                  const text = $(this).text().toLowerCase();
                  const match = !q || text.includes(q);
                  $(this).toggle(match);
                  if (match) visibleCount++;
                });
            
                // Hide section if no visible cards (when searching)
                if (q) {
                  section.toggle(visibleCount > 0);
                } else {
                  section.show(); // show all when query cleared
                }
            
                // Update the count badge
                const counter = section.find('summary span').eq(1);
                if (counter.length) {
                  const originalCount = counter.data('orig') || counter.text();
                  if (!counter.data('orig')) counter.data('orig', originalCount);
                  counter.text(q ? visibleCount : counter.data('orig'));
                }
              });
            }
            
            // Bind input with debounce
            const bindSearch = () => {
              const $input = $('#todo-search');
              if ($input.data('bound')) return;
              $input.on('input', debounce(e => applyTodoFilter(e.target.value), 200));
              $input.data('bound', true);
            };
            
            // Bind search after render
            setTimeout(bindSearch, 0);
            
            // Expand / Collapse all handlers
            $('#expand-all').on('click', () => {
                wrapper.find('details.todo-section').attr('open', true);
            });
            $('#collapse-all').on('click', () => {
                wrapper.find('details.todo-section').removeAttr('open');
            });
            
            // Fetch & render closed basket
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'ToDo',
                    filters: { allocated_to: frappe.session.user, status: 'Closed' },
                    fields: ['name','custom_title','description','priority','reference_type','reference_name','date'],
                    order_by: 'date desc',
                    limit_page_length: 500
                },
                callback: function (cr) {
                    const closed = cr.message || [];
                    const cards = closed.map(todo => {
                        const title = strip_html(todo.custom_title || todo.description || 'Untitled Task');
                        const refLine = (todo.reference_type && todo.reference_name)
                            ? `<br><small>Ref: ${todo.reference_type} ${todo.reference_name}</small>` : '';
                        const dueLine = todo.date
                            ? `<br><small class="text-muted">Due: ${frappe.datetime.str_to_user(todo.date)}</small>` : '';
                        return `
                            <div class="todo-card closed" style="margin-bottom:10px;padding:10px;border:1px solid #eee;border-radius:6px;">
                                <div>
                                    <b>${frappe.utils.escape_html(title)}</b><br>
                                    <small>Priority: ${todo.priority || '-'}</small>
                                    ${dueLine}
                                    ${refLine}
                                </div>
                                <div style="display:flex;justify-content:flex-end;margin-top:8px;">
                                    <button class="btn btn-xs btn-secondary reopen-todo" data-name="${todo.name}">Reopen</button>
                                </div>
                            </div>
                        `;
                    }).join('');
            
                    const closedSection = closed.length
                        ? `
                            <details class="todo-section" style="margin-bottom:10px;">
                                <summary style="cursor:pointer; user-select:none; padding:6px 8px; border:1px solid #e5e5e5; border-radius:6px; background:#fafafa; display:flex; align-items:center; justify-content:space-between;">
                                    <span>Closed</span>
                                    <span style="opacity:.7; font-size:12px;">${closed.length}</span>
                                </summary>
                                <div style="margin-top:8px;">${cards}</div>
                            </details>
                          `
                        : `
                            <details class="todo-section" style="margin-bottom:10px;">
                                <summary style="cursor:pointer; user-select:none; padding:6px 8px; border:1px solid #e5e5e5; border-radius:6px; background:#fafafa; display:flex; align-items:center; justify-content:space-between;">
                                    <span>Closed</span>
                                    <span style="opacity:.7; font-size:12px;">0</span>
                                </summary>
                                <div style="margin-top:8px;"><p style="margin:6px 0;">No closed ToDos.</p></div>
                            </details>
                          `;
            
                    wrapper.find('#closed-basket').html(closedSection);
            
                    // Bind reopen buttons
                    wrapper.find('.reopen-todo').on('click', function () {
                        const name = $(this).data('name');
                        frappe.call({
                            method: 'frappe.client.set_value',
                            args: { doctype: 'ToDo', name, fieldname: 'status', value: 'Open' },
                            callback: function () {
                                frappe.show_alert({ message: '♻️ ToDo reopened', indicator: 'blue' });
                                render_todo_dashboard(frm);
                            }
                        });
                    });
                }
            });

            
            // Expand / Collapse all handlers
            $('#expand-all').on('click', () => {
                wrapper.find('details.todo-section').attr('open', true);
            });
            $('#collapse-all').on('click', () => {
                wrapper.find('details.todo-section').removeAttr('open');
            });
            
            // Existing handlers
            $('#create-todo-btn').on('click', () => create_new_todo(frm));
            $('#view-closed-todos').on('click', (e) => { e.preventDefault(); show_closed_todos(frm); });
            
            wrapper.find('.close-todo').on('click', function () {
                const todoName = $(this).data('name');
                frappe.confirm('Are you sure you want to close this ToDo?', () => {
                    frappe.call({
                        method: 'frappe.client.set_value',
                        args: { doctype: 'ToDo', name: todoName, fieldname: 'status', value: 'Closed' },
                        callback: function () {
                            frappe.show_alert({ message: 'ToDo Closed', indicator: 'green' });
                            render_todo_dashboard(frm);
                        }
                    });
                });
            });
        }
    });
}

// Now add the missing create_new_todo function here
function create_new_todo(frm) {
    frappe.prompt([
        { fieldname: 'description', label: 'ToDo Description', fieldtype: 'Data', reqd: true },
        { fieldname: 'priority', label: 'Priority', fieldtype: 'Select', options: ['Low','Medium','High'], default: 'Medium' },
        { fieldname: 'date', label: 'Due Date', fieldtype: 'Date' }
    ],
    (values) => {
        frappe.call({
            method: 'frappe.client.insert',
            args: {
                doc: {
                    doctype: 'ToDo',
                    owner: frappe.session.user,
                    allocated_to: frappe.session.user, // ✅ ensure it appears in dashboard
                    description: values.description,
                    priority: values.priority,
                    date: values.date,
                    status: 'Open'
                }
            },
            callback: function () {
                frappe.show_alert({ message: '📝 New ToDo created', indicator: 'green' });
                render_todo_dashboard(frm);
            }
        });
    },
    'Create New ToDo',
    'Create');
}

function show_closed_todos(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'ToDo',
            filters: { allocated_to: frappe.session.user, status: 'Closed' },
            fields: ['name','custom_title','description','priority','reference_type','reference_name','date'],
            order_by: 'date asc'
        },
        callback: function (r) {
            const rows = r.message || [];
            if (!rows.length) { frappe.msgprint('No closed ToDos found.'); return; }

            const html = rows.map(todo => `
                <div class="closed-todo-block" style="margin-bottom:10px;padding:8px;border-bottom:1px solid #ddd;">
                    <b>${frappe.utils.escape_html(strip_html(todo.custom_title || todo.description || 'Untitled Task'))}</b><br>
                    <small>Priority: ${todo.priority || '-'}</small>
                    ${todo.date ? `<br><small>Due: ${frappe.datetime.str_to_user(todo.date)}</small>` : ''}
                    ${(todo.reference_type && todo.reference_name) ? `<br><small>Ref: ${todo.reference_type} ${todo.reference_name}</small>` : ''}
                    <br>
                    <button class="btn btn-xs btn-secondary reopen-todo-btn" data-name="${todo.name}">Reopen</button>
                </div>
            `).join('');

            const dialog = new frappe.ui.Dialog({
                title: '📁 Closed ToDos',
                fields: [{ fieldtype: 'HTML', fieldname: 'closed_todos_html', options: `<div style="max-height:350px;overflow-y:auto;">${html}</div>` }],
                primary_action_label: 'Close',
                primary_action() { dialog.hide(); }
            });

            dialog.show();

            setTimeout(() => {
                dialog.$wrapper.find('.reopen-todo-btn').on('click', function () {
                    const name = $(this).data('name');
                    frappe.call({
                        method: 'frappe.client.set_value',
                        args: { doctype: 'ToDo', name, fieldname: 'status', value: 'Open' },
                        callback: function () {
                            frappe.show_alert({ message: '♻️ ToDo reopened', indicator: 'blue' });
                            dialog.hide();
                            render_todo_dashboard(frm);
                        }
                    });
                });
            }, 200);
        }
    });
}
