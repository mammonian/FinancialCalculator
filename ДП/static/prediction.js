let selectedPeriod = 3;
    let selectedMethod = 0;
    let forecastChart;

    const methodExplanations = [
        "Цей метод по суті припускає, що майбутні тенденції будуть відображати минулі.",
        "Цей метод коригує прогнози, враховуючи очікуваний рівень інфляції, що дає більш реалістичні результати.",
        "Цей метод аналізує можливі майбутні результати на основі різних припущень (песимістичний, базовий, оптимістичний), допомагаючи оцінити ризики."
    ];

    function updateChart(data) {
        const allLabels = data.historical_labels.concat(data.forecast_labels);
        let datasets = [];

        if (data.historical_data && data.historical_data.length > 0) {
            datasets.push({
                label: 'Історичні дані',
                data: data.historical_data.concat(Array(data.forecast_labels.length).fill(null)),
                borderColor: 'rgba(255, 255, 255, 0.6)',
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                fill: false,
                tension: 0.3,
                pointRadius: 2,
                pointHoverRadius: 4,
                borderDash: [5, 5],
                segment: {
                    borderColor: ctx => {
                        if (ctx.p1DataIndex >= data.historical_labels.length -1) {
                           return 'rgba(255, 255, 255, 0.3)';
                        }
                        return 'rgba(255, 255, 255, 0.6)';
                    },
                    borderDash: ctx => {
                        if (ctx.p1DataIndex >= data.historical_labels.length -1) {
                            return [5,5];
                        }
                        return undefined;
                    }
                }
            });
        }

        if (data.method === "Сценарний аналіз") {
            const colors = {
                "Песимістичний": 'rgba(248,113,113,0.8)',
                "Базовий": 'rgba(99,102,241,0.8)',
                "Оптимістичний": 'rgba(34,197,94,0.8)'
            };
            const backgroundColors = {
                "Песимістичний": 'rgba(248,113,113,0.2)',
                "Базовий": 'rgba(99,102,241,0.2)',
                "Оптимістичний": 'rgba(34,197,94,0.2)'
            };

            Object.entries(data.scenario_predictions).forEach(([scenario, values]) => {
                datasets.push({
                    label: `Прогноз (${scenario})`,
                    data: Array(data.historical_labels.length).fill(null).concat(values),
                    borderColor: colors[scenario] || 'gray',
                    backgroundColor: backgroundColors[scenario] || 'rgba(128,128,128,0.2)',
                    fill: false,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    spanGaps: true
                });
            });
        } else if (data.monthly_forecast) {
            datasets.push({
                label: `Прогноз (${data.method})`,
                data: Array(data.historical_labels.length).fill(null).concat(data.monthly_forecast),
                borderColor: '#6c3df4',
                backgroundColor: 'rgba(108,61,244,0.3)',
                fill: 'origin',
                tension: 0.4,
                pointRadius: 4,
                pointHoverRadius: 6,
                spanGaps: true
            });
        }

        if (forecastChart) {
            forecastChart.data.labels = allLabels;
            forecastChart.data.datasets = datasets;
            forecastChart.update();
        } else {
            const ctx = document.getElementById('forecastChart').getContext('2d');
            forecastChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: allLabels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Прогноз фінансових показників (історичні та прогнозні дані)',
                            color: 'white',
                            font: {
                                size: 18,
                                weight: 'bold'
                            }
                        },
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: 'white',
                                font: {
                                    size: 14
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed.y !== null) {
                                        label += new Intl.NumberFormat('uk-UA', { style: 'currency', currency: 'UAH' }).format(context.parsed.y);
                                    }
                                    return label;
                                }
                            },
                            titleFont: { size: 16 },
                            bodyFont: { size: 14 },
                            padding: 10,
                            boxPadding: 5,
                            backgroundColor: 'rgba(0, 0, 0, 0.7)',
                            borderColor: '#6c3df4',
                            borderWidth: 1,
                            cornerRadius: 6,
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index',
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Час',
                                color: 'white',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            },
                            ticks: {
                                color: 'white',
                                font: {
                                    size: 12
                                }
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)',
                                drawBorder: false,
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Значення',
                                color: 'white',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            },
                            suggestedMin: 0,
                            ticks: {
                                color: 'white',
                                font: {
                                    size: 12
                                },
                                callback: function(value) {
                                    return new Intl.NumberFormat('uk-UA', { style: 'currency', currency: 'UAH', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value);
                                }
                            },
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)',
                                drawBorder: false,
                            }
                        }
                    },
                    elements: {
                        line: {
                            cubicInterpolationMode: 'monotone',
                            borderWidth: 3,
                        },
                        point: {
                            radius: 4,
                            hoverRadius: 6,
                            backgroundColor: '#6c3df4',
                            borderColor: 'white',
                            borderWidth: 1
                        }
                    }
                }
            });
        }
    }

    document.querySelectorAll('.period-button').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.period-button').forEach(btn => {
                btn.classList.remove('ring-2', 'ring-white');
            });
            button.classList.add('ring-2', 'ring-white');

            selectedPeriod = parseInt(button.id.split('-')[1]);
            document.getElementById("predict-button").click();
        });
    });

    document.querySelectorAll('input[name="method"]').forEach(radio => {
        radio.addEventListener('change', () => {
            selectedMethod = parseInt(radio.value);
            document.getElementById('method-explanation').textContent = methodExplanations[selectedMethod];
            document.getElementById("predict-button").click();
        });
    });

    document.getElementById("predict-button").addEventListener("click", () => {
        fetch("/api/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ period_months: selectedPeriod, method_index: selectedMethod })
        })
        .then(res => res.json())
        .then(data => {
            updateChart(data);
        })
        .catch(err => {
            console.error("Помилка:", err);
        });
    });

    document.getElementById('period-3').classList.add('ring-2', 'ring-white');
    document.querySelector('input[name="method"][value="0"]').checked = true;
    document.getElementById('method-explanation').textContent = methodExplanations[0];

    document.getElementById("predict-button").click();