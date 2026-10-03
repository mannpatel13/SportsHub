/**
 * SportsHub - Creative SaaS Client Application
 * Features: Dark/Light Mode, Interactive AI Simulator, Tactical Pitch, Live Scorer, Chart.js Analytics, Confetti & PDF Export
 */

document.addEventListener('DOMContentLoaded', () => {
    initThemeToggle();
    initCountUpAnimations();
    initModals();
    initTooltips();
});

/* ----------------------------------------------------
   1. THEME TOGGLE (Dark / Light Mode)
   ---------------------------------------------------- */
function initThemeToggle() {
    const themeBtn = document.getElementById('themeToggleBtn');
    const htmlEl = document.documentElement;
    
    // Check saved preference or default to dark
    const savedTheme = localStorage.getItem('sportshub-theme') || 'dark';
    htmlEl.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const currentTheme = htmlEl.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            htmlEl.setAttribute('data-theme', newTheme);
            localStorage.setItem('sportshub-theme', newTheme);
            updateThemeIcon(newTheme);

            // Re-render chart colors if active
            if (window.dispatchEvent) {
                window.dispatchEvent(new Event('resize'));
            }
        });
    }
}

function updateThemeIcon(theme) {
    const icon = document.getElementById('themeIcon');
    if (!icon) return;
    if (theme === 'dark') {
        icon.className = 'fas fa-sun';
    } else {
        icon.className = 'fas fa-moon';
    }
}

/* ----------------------------------------------------
   2. ANIMATED NUMBER COUNTERS
   ---------------------------------------------------- */
function initCountUpAnimations() {
    const counters = document.querySelectorAll('[data-counter]');
    counters.forEach(counter => {
        const target = parseFloat(counter.getAttribute('data-counter'));
        const duration = 1200; // ms
        const stepTime = 20;
        const totalSteps = duration / stepTime;
        const increment = target / totalSteps;
        let current = 0;

        const isDecimal = target % 1 !== 0;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                counter.innerText = isDecimal ? target.toFixed(1) : Math.round(target);
                clearInterval(timer);
            } else {
                counter.innerText = isDecimal ? current.toFixed(1) : Math.round(current);
            }
        }, stepTime);
    });
}

/* ----------------------------------------------------
   3. MODAL CONTROLLER
   ---------------------------------------------------- */
function initModals() {
    window.openModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    };

    window.closeModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    };

    // Close modal on click outside box
    // Promote modal overlays to <body>. The page content uses a transform animation,
    // which otherwise makes position: fixed relative to the scrolled content.
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        if (overlay.parentElement !== document.body) document.body.appendChild(overlay);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });
}

function initTooltips() {
    // Lucide icons or bootstrap tooltips if needed
}

/* ----------------------------------------------------
   4. TOAST NOTIFICATIONS
   ---------------------------------------------------- */
window.showToast = function(message, type = 'success') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = 'position: fixed; bottom: 24px; right: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 10px; pointer-events: none;';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bg = type === 'success' ? '#10B981' : (type === 'error' ? '#F43F5E' : '#3B82F6');
    toast.style.cssText = `background: #0F172A; color: #FFF; border-left: 4px solid ${bg}; padding: 14px 20px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); font-size: 0.88rem; font-weight: 600; display: flex; align-items: center; gap: 10px; pointer-events: auto; animation: fadeInUp 0.3s ease forwards;`;
    
    const iconClass = type === 'success' ? 'fa-check-circle' : (type === 'error' ? 'fa-exclamation-triangle' : 'fa-info-circle');
    toast.innerHTML = `<i class="fas ${iconClass}" style="color: ${bg}; font-size: 1.1rem;"></i> <span>${message}</span>`;
    
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
};

/* ----------------------------------------------------
   5. CONFETTI CELEBRATION
   ---------------------------------------------------- */
window.fireConfetti = function() {
    if (typeof confetti === 'function') {
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 }
        });
    }
};

/* ----------------------------------------------------
   6. PDF EXPORT HELPER
   ---------------------------------------------------- */
window.exportPageToPDF = function(elementId, filename = 'SportsHub_Report.pdf') {
    const el = document.getElementById(elementId);
    if (!el) return;

    if (typeof html2pdf !== 'undefined') {
        const opt = {
            margin:       10,
            filename:     filename,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { scale: 2, useCORS: true },
            jsPDF:        { unit: 'mm', format: 'a4', orientation: 'landscape' }
        };
        html2pdf().set(opt).from(el).save();
    } else {
        window.print();
    }
};
