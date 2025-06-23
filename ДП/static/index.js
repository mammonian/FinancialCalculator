
let todayExpensesChartInstance = null;
let cashFlowChartInstance = null;


const colors = ['#fb4676', '#9254de', '#ffe600', '#2ae4c3', '#6ecbff', '#00d084', '#ff9800', '#ff4081'];


async function updateDashboardData() {
    console.log("Updating dashboard data...");

    // Update monthly cash flow
    try {
        const res = await fetch("/api/monthly-flow");
        const data = await res.json();
        const income = data.income || 0;
        const expense = data.expense || 0;
        const balance = data.balance || 0;

        const incomePercent = income > 0 ? 100 : 0;
        const expensePercent = income > 0 ? Math.min((expense / income) * 100, 100) : 0;


        document.getElementById("incomeAmount").textContent = income.toLocaleString();
        document.getElementById("expenseAmount").textContent = expense.toLocaleString();
        document.getElementById("balanceAmount").textContent = balance.toLocaleString();

        document.getElementById("incomeBar").style.width = incomePercent + "%";
        document.getElementById("expenseBar").style.width = expensePercent + "%";
    } catch (err) {
        console.error('Error loading monthly flow:', err);
        // You can show an error message to the user here
    }

   
    const currentPeriodButton = document.querySelector('.period-btn.bg-\\[\\#6c3df4\\]');
    const currentPeriod = currentPeriodButton ? currentPeriodButton.getAttribute("data-period") : 'today';
    await loadExpenses(currentPeriod); 

  
    try {
        const res = await fetch('/api/daily-cashflow', { credentials: 'include' });
        if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
        const data = await res.json();

        
        if (cashFlowChartInstance) {
            cashFlowChartInstance.destroy();
        }

        const ctx2 = document.getElementById('cashFlowChart').getContext('2d');
        cashFlowChartInstance = new Chart(ctx2, {
            type: 'line',
            data: {
                labels: data.labels.map(d => {
                    const dt = new Date(d);
                    return dt.getDate() + '.' + (dt.getMonth() + 1);
                }),
                datasets: [
                    {
                        label: 'Доходи',
                        data: data.income,
                        borderColor: '#10b981',
                        backgroundColor: '#6ee7b7',
                        tension: 0.3
                    },
                    {
                        label: 'Витрати',
                        data: data.expense,
                        borderColor: '#ef4444',
                        backgroundColor: '#fca5a5',
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom', labels: { color: 'white' } }
                },
                scales: {
                    x: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                    y: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } }
                }
            }
        });
    } catch (err) {
        console.error('Error loading cash flow chart:', err);
    }

    try {
        const recordsResponse = await fetch('/api/get_records');
        const recordsData = await recordsResponse.json();
        const recordsTableBody = document.querySelector('.responsive-table tbody');
        recordsTableBody.innerHTML = ''; 

        if (recordsData.records && recordsData.records.length > 0) {
            recordsData.records.forEach((record, index) => { 
                const newRow = document.createElement('tr');
                newRow.classList.add('border-t', 'border-purple-500', 'table-row-with-actions');
                newRow.dataset.recordId = record[0]; 
                newRow.innerHTML = `
                    <td data-label="ID">${index + 1}</td> <!-- Changed to use index + 1 -->
                    <td data-label="Дата">${record[1].split(' ')[0]}</td>
                    <td data-label="Час">${record[1].split(' ')[1].substring(0, 5)}</td>
                    <td data-label="Категорія">${record[2]}</td>
                    <td data-label="Сума">${record[3]} грн</td>
                    <td data-label="Дії" class="delete-button-cell">
                        <button class="delete-btn text-red-500 hover:text-red-700 font-bold py-1 px-2 rounded-full text-lg leading-none transition-colors duration-200" data-id="${record[0]}">&times;</button>
                    </td>
                `;
                recordsTableBody.appendChild(newRow);
            });
        } else {
            recordsTableBody.innerHTML = `<tr><td colspan="6" class="text-center py-4">No records yet</td></tr>`;
        }
    } catch (err) {
        console.error('Error loading records:', err);
    }

    attachDeleteListeners();
}


/**
 * Attaches event listeners to delete buttons.
 * This function must be called whenever the DOM containing delete buttons is updated.
 */
function attachDeleteListeners() {
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        if (button.dataset.listenerAttached) {
            return;
        }
        button.dataset.listenerAttached = 'true'; 

        button.addEventListener('click', async (event) => {
            const recordId = event.currentTarget.dataset.id; 

            
            const confirmation = confirm(`Are you sure you want to delete record ID: ${recordId}?`);

            if (confirmation) {
                try {
                    const response = await fetch(`/api/transactions/${recordId}`, {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });

                    if (response.ok) {
                        console.log(`Record ${recordId} successfully deleted.`);
                        await updateDashboardData();
                    } else {
                        const errorData = await response.json();
                        console.error('Deletion error:', errorData.error);
                    }
                } catch (error) {
                    console.error('Network error during deletion:', error);
                }
            }
        });
    });
}


/**
 * Function to load and display the expenses chart for a specific period.
 * @param {string} period - Period for loading expenses (today, yesterday, week, month, etc.).
 */
function loadExpenses(period = 'today') {
    return fetch(`/api/expenses?period=${period}`)
        .then((res) => res.json())
        .then((data) => {
            const ctx = document.getElementById("todayExpensesChart").getContext("2d");
            const categories = data.categories;
            const labels = categories.map((c) => c.name);
            const amounts = categories.map((c) => c.amount);
            const total = data.total;

            document.querySelector("#todayExpensesChart")
                .parentElement.querySelector(".absolute").textContent = `${total.toLocaleString()} грн`;

            if (todayExpensesChartInstance) {
                todayExpensesChartInstance.destroy(); 
            }

            todayExpensesChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: amounts,
                        backgroundColor: colors.slice(0, labels.length),
                        borderWidth: 0
                    }]
                },
                options: {
                    cutout: '70%',
                    plugins: {
                        legend: { display: false }
                    }
                }
            });

            const list = document.getElementById("category-breakdown");
            categories.forEach((category, index) => {
                const percent = total > 0 ? (category.amount / total) * 100 : 0;
                const color = colors[index % colors.length];
                const li = document.createElement("li");
                li.innerHTML = `
                    <div class="flex justify-between items-center mb-1">
                        <div class="flex items-center space-x-2">
                            <span class="w-2 h-2 rounded-full" style="background-color: ${color};"></span>
                            <span>${category.name}</span>
                        </div>
                        <span class="font-semibold">${category.amount}</span>
                    </div>
                    <div class="w-full h-1 bg-white/20 rounded">
                        <div class="h-full rounded" style="width: ${percent.toFixed(2)}%; background-color: ${color};"></div>
                    </div>`;
                list.appendChild(li);
            });
        }).catch(err => console.error('Error loading expenses:', err));
}

// --- SCRIPT FOR MODAL WINDOW (CATEGORIES) ---
const typeButtons = document.querySelectorAll('#type-selector button');
const categoryButtons = document.querySelectorAll('.category-btn');
const hiddenCategoryInput = document.getElementById('selected-category-id');
const hiddenTypeInput = document.getElementById('selected-type');

function updateCategoryVisibility(selectedType) {
    categoryButtons.forEach(btn => {
        if (btn.dataset.type === selectedType) {
            btn.style.display = 'inline-block';
        } else {
            btn.style.display = 'none';
            btn.classList.remove('bg-[#6c3df4]');
            btn.classList.add('bg-[#442277]');
            if (hiddenCategoryInput.value === btn.dataset.categoryId) {
                hiddenCategoryInput.value = '';
            }
        }
    });
}

// --- MAIN DOMContentLoaded LISTENER ---
document.addEventListener("DOMContentLoaded", async () => {
    updateCategoryVisibility('expense');

    typeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            typeButtons.forEach(b => {
                b.classList.remove('bg-[#6c3df4]');
                b.classList.add('bg-[#442277]');
            });
            btn.classList.remove('bg-[#442277]');
            btn.classList.add('bg-[#6c3df4]');
            hiddenTypeInput.value = btn.dataset.type;
            updateCategoryVisibility(btn.dataset.type);
            hiddenCategoryInput.value = '';
            categoryButtons.forEach(b => {
                b.classList.remove('bg-[#6c3df4]');
                b.classList.add('bg-[#442277]');
            });
        });
    });

    categoryButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            categoryButtons.forEach(b => {
                // ВИПРАВЛЕНО: Прибираємо подвійне екранування для classList.remove/add
                if (b.dataset.type === hiddenTypeInput.value) { 
                    b.classList.remove('bg-[#6c3df4]');
                    b.classList.add('bg-[#442277]');
                }
            });
            // ВИПРАВЛЕНО: Прибираємо подвійне екранування для classList.remove/add
            btn.classList.remove('bg-[#442277]');
            btn.classList.add('bg-[#6c3df4]');
            hiddenCategoryInput.value = btn.dataset.categoryId;
        });
    });

    // Add listeners to period buttons
    const periodButtons = document.querySelectorAll(".period-btn");
    periodButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            periodButtons.forEach(b => {
                
                b.classList.remove('bg-[#6c3df4]');
                b.classList.add('bg-[#442277]');
            });
            
            btn.classList.remove('bg-[#442277]');
            btn.classList.add('bg-[#6c3df4]');
            const period = btn.getAttribute("data-period");
            loadExpenses(period); // Update chart on click
        });
    });

    // Initial loading of all dashboard data
    await updateDashboardData();
});
