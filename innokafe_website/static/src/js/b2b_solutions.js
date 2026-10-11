/** @odoo-module **/

/**
 * InnoKafe B2B Solutions Interactive Enhancements
 * Cardless Liquid Spatial UI tier selection and smooth scroll to inquiry form.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Select tier button handler
    const tierButtons = document.querySelectorAll('a[href="#b2b_form"]');
    tierButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const formSection = document.getElementById('b2b_form');
            if (formSection) {
                e.preventDefault();
                formSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
});

export default {};
