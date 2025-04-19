/**
 * Dashboard.js
 * Handles interactive features for the dashboard page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize any DataTables if they exist
    if (typeof $.fn.DataTable !== 'undefined' && $('#roomsTable').length) {
        $('#roomsTable').DataTable({
            pageLength: 10,
            responsive: true,
            language: {
                search: "",
                searchPlaceholder: "Search rooms..."
            }
        });
    }

    // Fetch activity data for the chart (last 30 days by default)
    function fetchActivityData() {
        // In a real implementation, this would be an API call
        // For now, we'll use the data initialized in the dashboard.html template
        
        // We'll load activity data from each user's rooms
        const roomIds = document.querySelectorAll('[data-room-id]');
        
        if (roomIds.length > 0) {
            Promise.all(Array.from(roomIds).map(el => {
                const roomId = el.getAttribute('data-room-id');
                return fetch(`/api/analytics/room/${roomId}?days=30`)
                    .then(response => response.json());
            }))
            .then(results => {
                // Combine data from all rooms
                updateActivityChart(combineChartData(results));
            })
            .catch(error => {
                console.error('Error fetching activity data:', error);
            });
        }
    }
    
    // Combine chart data from multiple rooms
    function combineChartData(dataArray) {
        if (!dataArray || dataArray.length === 0) return null;
        
        // Create a combined dataset
        const combined = {
            labels: [],
            datasets: [
                {
                    label: 'Views',
                    data: [],
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                },
                {
                    label: 'Downloads',
                    data: [],
                    borderColor: 'rgba(153, 102, 255, 1)',
                    backgroundColor: 'rgba(153, 102, 255, 0.2)',
                    tension: 0.1
                }
            ]
        };
        
        // Get all unique dates
        const allDates = new Set();
        dataArray.forEach(data => {
            if (data && data.labels) {
                data.labels.forEach(date => allDates.add(date));
            }
        });
        
        // Sort dates
        combined.labels = Array.from(allDates).sort();
        
        // Initialize data arrays with zeros
        combined.labels.forEach(() => {
            combined.datasets[0].data.push(0);
            combined.datasets[1].data.push(0);
        });
        
        // Add data from each room
        dataArray.forEach(data => {
            if (!data || !data.labels || !data.datasets) return;
            
            data.labels.forEach((date, i) => {
                const dateIndex = combined.labels.indexOf(date);
                if (dateIndex !== -1) {
                    // Views
                    if (data.datasets[0] && data.datasets[0].data) {
                        combined.datasets[0].data[dateIndex] += (data.datasets[0].data[i] || 0);
                    }
                    
                    // Downloads
                    if (data.datasets[1] && data.datasets[1].data) {
                        combined.datasets[1].data[dateIndex] += (data.datasets[1].data[i] || 0);
                    }
                }
            });
        });
        
        return combined;
    }
    
    // Update the activity chart with new data
    function updateActivityChart(chartData) {
        const ctx = document.getElementById('activityChart');
        if (!ctx) return;
        
        if (window.activityChart) {
            // Update existing chart
            window.activityChart.data.labels = chartData.labels;
            window.activityChart.data.datasets[0].data = chartData.datasets[0].data;
            window.activityChart.data.datasets[1].data = chartData.datasets[1].data;
            window.activityChart.update();
        } else {
            // Create new chart
            window.activityChart = new Chart(ctx, {
                type: 'line',
                data: chartData || {
                    labels: [],
                    datasets: [
                        {
                            label: 'Views',
                            data: [],
                            borderColor: 'rgba(75, 192, 192, 1)',
                            backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            tension: 0.1
                        },
                        {
                            label: 'Downloads',
                            data: [],
                            borderColor: 'rgba(153, 102, 255, 1)',
                            backgroundColor: 'rgba(153, 102, 255, 0.2)',
                            tension: 0.1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        },
                        legend: {
                            position: 'top',
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                        }
                    }
                }
            });
        }
    }
    
    // Initialize room cards with hover effects
    function initRoomCards() {
        document.querySelectorAll('.dashboard-card').forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.classList.add('shadow');
            });
            
            card.addEventListener('mouseleave', function() {
                this.classList.remove('shadow');
            });
        });
    }
    
    // Initialize tooltips
    function initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Initialize the dashboard
    function initDashboard() {
        initRoomCards();
        initTooltips();
        
        // If there's an activity chart on the page, fetch data
        if (document.getElementById('activityChart')) {
            fetchActivityData();
        }
    }
    
    // Run initialization
    initDashboard();
});
