/**
 * Analytics.js
 * Handles interactive features for the analytics page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable for activity log
    if (typeof $.fn.DataTable !== 'undefined' && $('#activityTable').length) {
        $('#activityTable').DataTable({
            order: [[1, 'desc']], // Sort by date descending
            pageLength: 10,
            language: {
                search: "",
                searchPlaceholder: "Search activities..."
            }
        });
    }
    
    // Handle time period selector changes
    const periodSelectors = document.querySelectorAll('input[name="time-period"]');
    periodSelectors.forEach(radio => {
        radio.addEventListener('change', function() {
            updateChartData(this.value);
        });
    });
    
    // Fetch chart data for the selected time period
    function updateChartData(days) {
        const roomId = window.location.pathname.split('/').filter(Boolean)[1];
        if (!roomId) return;
        
        // Show loading state
        const chartContainer = document.querySelector('.chart-container');
        if (chartContainer) {
            chartContainer.classList.add('loading');
            chartContainer.style.opacity = '0.6';
        }
        
        fetch(`/api/analytics/room/${roomId}?days=${days}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                updateChart(data);
                if (chartContainer) {
                    chartContainer.classList.remove('loading');
                    chartContainer.style.opacity = '1';
                }
            })
            .catch(error => {
                console.error('Error fetching chart data:', error);
                if (chartContainer) {
                    chartContainer.classList.remove('loading');
                    chartContainer.style.opacity = '1';
                }
            });
    }
    
    // Update the chart with new data
    function updateChart(data) {
        const ctx = document.getElementById('activityChart');
        if (!ctx) return;
        
        if (window.activityChart) {
            // Update existing chart
            window.activityChart.data.labels = data.labels;
            window.activityChart.data.datasets = data.datasets;
            window.activityChart.update();
        } else {
            // Create new chart if it doesn't exist yet
            window.activityChart = new Chart(ctx, {
                type: 'line',
                data: data,
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
    
    // Initialize copy link buttons
    function initCopyButtons() {
        document.querySelectorAll('.copy-link').forEach(button => {
            button.addEventListener('click', function() {
                const link = this.getAttribute('data-link');
                if (!link) return;
                
                navigator.clipboard.writeText(link)
                    .then(() => {
                        // Show success feedback
                        const originalHTML = this.innerHTML;
                        this.innerHTML = '<i data-feather="check"></i>';
                        feather.replace();
                        
                        // Reset after a delay
                        setTimeout(() => {
                            this.innerHTML = originalHTML;
                            feather.replace();
                        }, 2000);
                    })
                    .catch(err => {
                        console.error('Failed to copy text: ', err);
                    });
            });
        });
    }
    
    // Initialize link cards with hover effects
    function initLinkCards() {
        document.querySelectorAll('.link-card').forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.boxShadow = '0 0.5rem 1rem rgba(0, 0, 0, 0.15)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.boxShadow = '';
            });
        });
    }
    
    // Generate downloadable analytics report
    function generateReport() {
        if (!window.activityChart) return;
        
        const roomName = document.querySelector('h1').textContent.replace('Analytics: ', '');
        const timeRange = document.querySelector('input[name="time-period"]:checked').value;
        const timeRangeText = timeRange === '7' ? '7 Days' : 
                            timeRange === '30' ? '30 Days' : 
                            timeRange === '90' ? '90 Days' : 'All Time';
        
        // Get stats from the page
        const totalViews = document.querySelector('.stats-card:nth-child(1) .stats-value').textContent;
        const totalDownloads = document.querySelector('.stats-card:nth-child(2) .stats-value').textContent;
        const totalLinkAccess = document.querySelector('.stats-card:nth-child(3) .stats-value').textContent;
        
        // Create report content
        let reportContent = `Analytics Report for ${roomName}\n`;
        reportContent += `Time Range: ${timeRangeText}\n`;
        reportContent += `Generated: ${new Date().toLocaleString()}\n\n`;
        reportContent += `Total Views: ${totalViews}\n`;
        reportContent += `Total Downloads: ${totalDownloads}\n`;
        reportContent += `Total Link Access: ${totalLinkAccess}\n\n`;
        reportContent += `Daily Activity:\n`;
        
        // Add chart data
        const labels = window.activityChart.data.labels;
        const viewsData = window.activityChart.data.datasets[0].data;
        const downloadsData = window.activityChart.data.datasets[1].data;
        const linkAccessData = window.activityChart.data.datasets[2].data;
        
        for (let i = 0; i < labels.length; i++) {
            reportContent += `${labels[i]}: Views: ${viewsData[i]}, Downloads: ${downloadsData[i]}, Link Access: ${linkAccessData[i]}\n`;
        }
        
        // Create download link
        const blob = new Blob([reportContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analytics_report_${roomName.replace(/\s+/g, '_').toLowerCase()}_${timeRangeText.replace(/\s+/g, '_').toLowerCase()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    // Add report generation button if not already present
    function addReportButton() {
        const headerDiv = document.querySelector('.d-flex.justify-content-between.align-items-center');
        if (!headerDiv || document.getElementById('generateReportBtn')) return;
        
        const reportBtn = document.createElement('button');
        reportBtn.id = 'generateReportBtn';
        reportBtn.className = 'btn btn-outline-primary ms-2';
        reportBtn.innerHTML = '<i data-feather="file-text" class="me-1"></i> Export Report';
        reportBtn.addEventListener('click', generateReport);
        
        // Add after the "Back to Room" button
        headerDiv.querySelector('a').after(reportBtn);
        feather.replace();
    }
    
    // Initialize the analytics page
    function initAnalytics() {
        // Setup the time period selector
        const defaultPeriod = document.querySelector('input[name="time-period"]:checked');
        if (defaultPeriod) {
            updateChartData(defaultPeriod.value);
        } else {
            // Default to 30 days if nothing is checked
            updateChartData(30);
        }
        
        initCopyButtons();
        initLinkCards();
        addReportButton();
    }
    
    // Run initialization
    initAnalytics();
});
