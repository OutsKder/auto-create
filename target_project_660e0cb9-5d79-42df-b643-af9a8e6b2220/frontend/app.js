// 基础服务地址，默认启动在 8000
const API_BASE_URL = 'http://127.0.0.1:8000/api';

// DOM 元素引用
const itemListEl = document.getElementById('itemList');
const formEl = document.getElementById('addItemForm');

// 统一获取列表方法 (供 Agent 微调扩展，如添加分页参数)
async function fetchItems() {
    try {
        const response = await fetch(`${API_BASE_URL}/items`);
        const json = await response.json();
        
        if (json.code === 200) {
            renderList(json.data);
        } else {
            itemListEl.innerHTML = `<li class="list-group-item text-danger">数据获取失败：${json.message}</li>`;
        }
    } catch (error) {
        console.error("请求失败", error);
        itemListEl.innerHTML = `<li class="list-group-item text-danger">后端尚未启动或网络异常！</li>`;
    }
}

// 统一渲染逻辑
function renderList(items) {
    itemListEl.innerHTML = '';
    if (items.length === 0) {
        itemListEl.innerHTML = '<li class="list-group-item text-center text-muted">毫无数据，请在左侧添加</li>';
        return;
    }
    
    items.forEach(item => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-start';
        
        // 使用后端返回的 low_stock_warning 标识进行渲染
        let stockBadge = '';
        if (item.low_stock_warning) {
            stockBadge = `<span class="badge bg-danger ms-2">库存告急 (${item.current_stock})</span>`;
        } else {
            stockBadge = `<span class="badge bg-success ms-2">充足 (${item.current_stock})</span>`;
        }
        
        li.innerHTML = `
            <div class="ms-2 me-auto" style="flex: 1;">
                <div class="d-flex align-items-center mb-1">
                    <h6 class="mb-0 fw-bold">${item.id}. ${item.name}</h6>
                    ${stockBadge}
                </div>
                <p class="mb-1 text-muted small">${item.description || '暂无描述'}</p>
                <div class="row mt-2">
                    <div class="col-6"><small class="text-primary">单价: ¥${parseFloat(item.unit_price).toFixed(2)}</small></div>
                    <div class="col-6 text-end"><small class="text-secondary">库存: ${item.current_stock}</small></div>
                </div>
            </div>
        `;
        itemListEl.appendChild(li);
    });
}

// 提交表单逻辑
formEl.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('itemName').value;
    const desc = document.getElementById('itemDesc').value;
    const price = parseFloat(document.getElementById('itemPrice').value) || 0.00;
    const stock = parseInt(document.getElementById('itemStock').value) || 0;

    const payload = {
        name: name,
        description: desc,
        unit_price: price,
        current_stock: stock
    };

    try {
        const res = await fetch(`${API_BASE_URL}/items`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const json = await res.json();
        if (json.code === 200) {
            // 添加成功后重置表单并重新获取列表
            document.getElementById('itemName').value = '';
            document.getElementById('itemDesc').value = '';
            document.getElementById('itemPrice').value = '0.00';
            document.getElementById('itemStock').value = '0';
            fetchItems();
        } else {
            alert("添加失败：" + json.message);
        }
    } catch (err) {
        alert("网络请求失败，请确保后端服务已启动在 8000 端口！\n" + err);
    }
});

// 初始化：页面载入自动拉取一次数据
fetchItems();
