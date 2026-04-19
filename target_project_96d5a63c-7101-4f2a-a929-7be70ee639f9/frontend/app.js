const API_BASE = 'http://127.0.0.1:8000/api/todos';

// 状态管理
let todos = [];
let currentFilter = 'all';
let isOfflineMode = false;
let fallbackId = 1000;

// DOM 元素引用
const DOM = {
    list: document.getElementById('todoList'),
    form: document.getElementById('addTodoForm'),
    input: document.getElementById('todoTitle'),
    count: document.getElementById('todoCount'),
    filters: document.querySelectorAll('.filter-btn')
};

// 缺省的离线假数据（正式展示用）
const fallbackData = [
    { id: 1, title: "完善待办事项 (Todo) 的后端 CRUD 逻辑", completed: true },
    { id: 2, title: "将前台界面设计得漂亮一点", completed: true },
    { id: 3, title: "体验智能飞书 Agent 生成代码应用", completed: false }
];

// 初始化加载
async function loadTodos() {
    DOM.list.innerHTML = `<li class="list-group-item text-center bg-transparent border-0 py-5"><div class="spinner-border text-primary"></div></li>`;
    try {
        if(isOfflineMode) throw new Error("Offline Active");
        const res = await fetch(API_BASE);
        if (!res.ok) throw new Error("API Error");
        const data = await res.json();
        todos = data.data;
    } catch (error) {
        if(!isOfflineMode) {
            isOfflineMode = true;
        }
        todos = [...fallbackData];
    }
    render();
}

// 添加任务
async function addTodo(e) {
    e.preventDefault();
    const title = DOM.input.value.trim();
    if (!title) return;
    DOM.input.value = '';

    try {
        if(isOfflineMode) throw new Error("Offline Active");
        const res = await fetch(API_BASE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, completed: false })
        });
        const data = await res.json();
        todos.unshift(data.data);
        render();
    } catch (error) {
        fallbackId++;
        todos.unshift({ id: fallbackId, title, completed: false });
        render();
    }
}

// 切换状态
window.toggleTodo = async function(id) {
    const todo = todos.find(t => t.id === id);
    if (!todo) return;
    
    const newStatus = !todo.completed;
    todo.completed = newStatus;
    render(); 

    if (isOfflineMode) return;

    try {
        const res = await fetch(`${API_BASE}/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ completed: newStatus })
        });
        if (!res.ok) throw new Error("Update failed");
    } catch (error) {
        isOfflineMode = true;
    }
}

// 带有物理动画的删除
window.deleteTodoWithAnim = async function(id, btnElement) {
    const li = btnElement.closest('.todo-item');
    if (li) {
        li.style.animation = 'slideOut 0.4s cubic-bezier(0.55, 0.085, 0.68, 0.53) forwards';
    }
    
    setTimeout(async () => {
        try {
            if(isOfflineMode) throw new Error("Offline Active");
            await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
        } catch (error) {
        }
        todos = todos.filter(t => t.id !== id);
        render();
    }, 400);
}

// 渲染视图
function render() {
    DOM.list.innerHTML = '';
    
    let filtered = todos;
    if (currentFilter === 'active') filtered = todos.filter(t => !t.completed);
    if (currentFilter === 'completed') filtered = todos.filter(t => t.completed);

    const activeCount = todos.filter(t => !t.completed).length;
    DOM.count.innerHTML = `<i class="bi bi-activity text-primary me-1"></i>${activeCount} 个任务待处理`;

    if (filtered.length === 0) {
        DOM.list.innerHTML = `
            <li class="list-group-item text-center bg-transparent border-0 py-5 text-muted">
                <i class="bi bi-inboxes" style="font-size: 2.5rem; opacity: 0.5;"></i>
                <p class="mt-3 mb-0">这里空空如也，来点灵感吧~</p>
            </li>
        `;
        return;
    }

    filtered.forEach((todo, index) => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center bg-transparent border-0 mb-2 shadow-sm todo-item';
        li.style.animation = `slideIn 0.4s ease-out forwards ${index * 0.05}s`;
        li.style.opacity = '0'; 
        li.style.borderRadius = '12px';
        li.style.background = 'rgba(255, 255, 255, 0.5) !important';
        
        li.innerHTML = `
            <div class="d-flex align-items-center w-100 pe-3" onclick="toggleTodo(${todo.id})" style="cursor:pointer">
                <div class="custom-checkbox me-3 ${todo.completed ? 'checked' : ''}" style="width: 24px; height: 24px; border: 2px solid #ccc; border-radius: 6px; transition: all 0.2s; display:flex; align-items:center; justify-content:center; ${todo.completed ? 'background-color: #0d6efd; border-color: #0d6efd; transform: scale(1.1);' : ''}">
                    ${todo.completed ? '<i class="bi bi-check text-white fs-5"></i>' : ''}
                </div>
                <span class="todo-text ${todo.completed ? 'text-decoration-line-through text-muted' : 'fw-medium text-dark'}">
                    ${todo.title}
                </span>
            </div>
            <button class="btn btn-sm text-danger opacity-50 hover-opacity-100 delete-btn border-0" onclick="event.stopPropagation(); deleteTodoWithAnim(${todo.id}, this)">
                <i class="bi bi-trash3 fs-5"></i>
            </button>
        `;
        DOM.list.appendChild(li);
    });
}

// 事件监听
DOM.form.addEventListener('submit', addTodo);
DOM.filters.forEach(radio => {
    radio.addEventListener('change', (e) => {
        currentFilter = e.target.value;
        render();
    });
});

// 追加动态动画样式
const extraCSS = document.createElement("style");
extraCSS.textContent = `
    @keyframes slideIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes slideOut { to { opacity: 0; transform: translateX(100px); } }
    .todo-item:hover { background: rgba(255, 255, 255, 0.8) !important; transform: scale(1.01); transition: all 0.2s; }
    .hover-opacity-100:hover { opacity: 1 !important; transform: scale(1.1); transition: all 0.2s; }
`;
document.head.appendChild(extraCSS);

// 启动入口
loadTodos();