document.addEventListener('DOMContentLoaded', function () {
    var dataEl = document.getElementById('measurement-history-data');
    if (!dataEl) {
        return;
    }

    var history = JSON.parse(dataEl.textContent);
    if (!history.length) {
        return;
    }

    var labels = history.map(function (entry) { return entry.date; });

    var charts = [
        { canvasId: 'weightChart', field: 'weight', label: 'Peso (kg)', color: '#8bbb31' },
        { canvasId: 'heightChart', field: 'height', label: 'Altura (cm)', color: '#3b82f6' },
        { canvasId: 'imcChart', field: 'imc', label: 'IMC', color: '#f59e0b' },
        { canvasId: 'metabolismoBasalChart', field: 'metabolismo_basal', label: 'Metabolismo basal', color: '#ef4444' },
        { canvasId: 'gastoEnergeticoChart', field: 'gasto_energetico', label: 'Gasto energético', color: '#8b5cf6' },
    ];

    charts.forEach(function (chartConfig) {
        var canvas = document.getElementById(chartConfig.canvasId);
        if (!canvas) {
            return;
        }

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: chartConfig.label,
                    data: history.map(function (entry) { return entry[chartConfig.field]; }),
                    borderColor: chartConfig.color,
                    backgroundColor: chartConfig.color,
                    spanGaps: true,
                    tension: 0.2,
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: { beginAtZero: false },
                },
            },
        });
    });
});
