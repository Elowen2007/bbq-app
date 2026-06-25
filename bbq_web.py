from flask import Flask, render_template_string, request, jsonify
from collections import defaultdict

app = Flask(__name__)

# 菜单数据（按你家实际情况修改）
MENU = {
    "羊肉串": 3.0,
    "牛肉串": 3.5,
    "鸡翅": 8.0,
    "烤鱼": 25.0,
    "烤茄子": 10.0,
    "烤韭菜": 8.0,
    "啤酒": 6.0,
    "饮料": 5.0,
    "烤馒头": 2.0,
}

# 订单存储：{桌号: [{"name": 菜名, "qty": 数量, "price": 单价}, ...]}
orders = defaultdict(list)

# HTML 模板（响应式设计，适配手机）
HTML = '''
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>烧烤摊点单</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; padding: 10px; }
        .header { background: #ff5722; color: white; padding: 10px; text-align: center; font-size: 20px; font-weight: bold; }
        .section { background: white; margin: 10px 0; padding: 10px; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .flex-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
        .flex-grow { flex: 1; min-width: 100px; }
        button { padding: 8px 12px; background: #ff5722; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:active { background: #e64a19; }
        button.secondary { background: #999; }
        select, input { padding: 8px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; }
        .menu-item { padding: 10px; border-bottom: 1px solid #eee; cursor: pointer; user-select: none; }
        .menu-item.selected { background: #ffe0b2; }
        .order-table { width: 100%; border-collapse: collapse; }
        .order-table td, .order-table th { padding: 8px; border-bottom: 1px solid #eee; text-align: left; }
        .total { font-size: 18px; font-weight: bold; color: #d32f2f; text-align: right; margin-top: 10px; }
        .danger { background: #d32f2f; }
        .qty-input { width: 60px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">🔥 烧烤摊点单系统</div>

        <!-- 桌号管理 -->
        <div class="section">
            <div class="flex-row">
                <label>桌号：</label>
                <select id="tableSelect" onchange="loadOrder()">
                    <option value="">-- 请选择 --</option>
                </select>
                <input type="text" id="newTableName" placeholder="新桌号" style="width:80px;">
                <button onclick="addTable()">新建桌</button>
                <button class="secondary" onclick="deleteTable()">删除桌</button>
            </div>
        </div>

        <!-- 菜单 -->
        <div class="section">
            <h3>📋 菜单</h3>
            <div id="menuList">
                {% for item, price in menu.items() %}
                <div class="menu-item" onclick="selectItem(this)" data-name="{{ item }}" data-price="{{ price }}">
                    {{ item }} - ¥{{ "%.1f"|format(price) }}
                </div>
                {% endfor %}
            </div>
            <div class="flex-row" style="margin-top:10px;">
                <label>数量：</label>
                <input type="number" id="quantity" class="qty-input" value="1" min="1" max="99">
                <button onclick="addItem()">➕ 添加</button>
            </div>
        </div>

        <!-- 当前桌订单 -->
        <div class="section">
            <h3>📝 <span id="currentTableTitle">请选择桌号</span></h3>
            <table class="order-table">
                <thead><tr><th>菜品</th><th>数量</th><th>小计</th></tr></thead>
                <tbody id="orderBody"></tbody>
            </table>
            <div class="total" id="totalAmount">合计：¥0.00</div>
            <button class="danger" onclick="checkout()" style="margin-top:10px;">💵 结账（清空）</button>
        </div>
    </div>

    <script>
        // 当前选中的菜品
        let selectedItem = null;
        let selectedName = '';
        let selectedPrice = 0;

        // 初始化桌号下拉
        async function loadTables() {
            const resp = await fetch('/api/tables');
            const data = await resp.json();
            const select = document.getElementById('tableSelect');
            select.innerHTML = '<option value="">-- 请选择 --</option>';
            data.tables.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t;
                opt.textContent = t;
                select.appendChild(opt);
            });
        }

        // 新建桌号
        async function addTable() {
            const name = document.getElementById('newTableName').value.trim();
            if (!name) return alert('请输入桌号');
            const resp = await fetch('/api/add_table', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({table: name})
            });
            const data = await resp.json();
            if (data.status === 'ok') {
                document.getElementById('newTableName').value = '';
                await loadTables();
                document.getElementById('tableSelect').value = name;
                loadOrder();
            } else {
                alert(data.msg);
            }
        }

        // 删除当前桌号
        async function deleteTable() {
            const table = document.getElementById('tableSelect').value;
            if (!table) return alert('请先选择桌号');
            if (!confirm('确定删除桌号 ' + table + ' 及所有订单吗？')) return;
            const resp = await fetch('/api/delete_table', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({table: table})
            });
            const data = await resp.json();
            if (data.status === 'ok') {
                await loadTables();
                document.getElementById('tableSelect').value = '';
                loadOrder();
            }
        }

        // 选中菜品
        function selectItem(el) {
            if (selectedItem) selectedItem.classList.remove('selected');
            el.classList.add('selected');
            selectedItem = el;
            selectedName = el.dataset.name;
            selectedPrice = parseFloat(el.dataset.price);
        }

        // 添加菜品到当前桌
        async function addItem() {
            const table = document.getElementById('tableSelect').value;
            if (!table) return alert('请先选择桌号');
            if (!selectedName) return alert('请先点击菜单中的菜品');
            const qty = parseInt(document.getElementById('quantity').value);
            if (isNaN(qty) || qty < 1) return alert('数量至少为1');
            const resp = await fetch('/api/add_order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({table: table, name: selectedName, qty: qty})
            });
            const data = await resp.json();
            if (data.status === 'ok') {
                loadOrder();
            } else {
                alert(data.msg);
            }
        }

        // 加载当前桌订单
        async function loadOrder() {
            const table = document.getElementById('tableSelect').value;
            if (!table) {
                document.getElementById('currentTableTitle').textContent = '请选择桌号';
                document.getElementById('orderBody').innerHTML = '';
                document.getElementById('totalAmount').textContent = '合计：¥0.00';
                return;
            }
            document.getElementById('currentTableTitle').textContent = '桌号：' + table;
            const resp = await fetch('/api/get_order/' + table);
            const data = await resp.json();
            const tbody = document.getElementById('orderBody');
            tbody.innerHTML = '';
            let total = 0;
            data.items.forEach(item => {
                const row = tbody.insertRow();
                row.insertCell().textContent = item.name;
                row.insertCell().textContent = item.qty;
                const subtotal = item.qty * item.price;
                row.insertCell().textContent = '¥' + subtotal.toFixed(1);
                total += subtotal;
            });
            document.getElementById('totalAmount').textContent = '合计：¥' + total.toFixed(2);
        }

        // 结账
        async function checkout() {
            const table = document.getElementById('tableSelect').value;
            if (!table) return alert('请先选择桌号');
            const resp = await fetch('/api/get_order/' + table);
            const data = await resp.json();
            let total = 0;
            data.items.forEach(item => total += item.qty * item.price);
            if (!confirm('桌号 ' + table + ' 合计 ¥' + total.toFixed(2) + '\\n确定结账并清空吗？')) return;
            await fetch('/api/checkout/' + table, {method: 'POST'});
            loadOrder();
        }

        // 页面加载时初始化
        window.onload = function() {
            loadTables();
            // 监听桌号下拉变化
            document.getElementById('tableSelect').addEventListener('change', loadOrder);
        };
    </script>
</body>
</html>
'''

# ---------- 路由 ----------
@app.route('/')
def index():
    return render_template_string(HTML, menu=MENU)

@app.route('/api/tables')
def get_tables():
    return jsonify({'tables': sorted(orders.keys())})

@app.route('/api/add_table', methods=['POST'])
def add_table():
    data = request.get_json()
    table = data.get('table', '').strip()
    if not table:
        return jsonify({'status': 'error', 'msg': '桌号不能为空'})
    if table in orders:
        return jsonify({'status': 'error', 'msg': f'桌号 {table} 已存在'})
    orders[table] = []
    return jsonify({'status': 'ok'})

@app.route('/api/delete_table', methods=['POST'])
def delete_table():
    data = request.get_json()
    table = data.get('table', '').strip()
    if table in orders:
        del orders[table]
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'msg': '桌号不存在'})

@app.route('/api/add_order', methods=['POST'])
def add_order():
    data = request.get_json()
    table = data.get('table')
    name = data.get('name')
    qty = int(data.get('qty', 1))
    if table not in orders:
        return jsonify({'status': 'error', 'msg': '桌号不存在'})
    if name not in MENU:
        return jsonify({'status': 'error', 'msg': '菜品不在菜单中'})
    orders[table].append({'name': name, 'qty': qty, 'price': MENU[name]})
    return jsonify({'status': 'ok'})

@app.route('/api/get_order/<table>')
def get_order(table):
    if table in orders:
        return jsonify({'items': orders[table]})
    return jsonify({'items': []})

@app.route('/api/checkout/<table>', methods=['POST'])
def checkout(table):
    if table in orders:
        orders[table] = []
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)