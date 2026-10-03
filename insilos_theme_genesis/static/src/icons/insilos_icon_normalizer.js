/* Insilos Phosphor Icon Normalizer */

/**
 * Insilos Phosphor Icon Normalizer & Compatibility Engine
 * Automatically upgrades legacy FontAwesome icon glyphs in the live DOM
 * to Phosphor Duotone icon font architecture, ensuring zero legacy icon signatures.
 */

const FA_TO_PHOSPHOR_MAP = {
    'fa-folder-o': 'ph-folder',
    'fa-folder': 'ph-folder',
    'fa-info-circle': 'ph-info',
    'fa-play': 'ph-play',
    'fa-plus': 'ph-plus',
    'fa-star': 'ph-star',
    'fa-pencil': 'ph-pencil-simple',
    'fa-send': 'ph-paper-plane-tilt',
    'fa-paper-plane': 'ph-paper-plane-tilt',
    'fa-long-arrow-right': 'ph-arrow-right',
    'fa-caret-down': 'ph-caret-down',
    'fa-caret-right': 'ph-caret-right',
    'fa-lightbulb-o': 'ph-lightbulb',
    'fa-refresh': 'ph-arrows-clockwise',
    'fa-navicon': 'ph-list',
    'fa-bars': 'ph-list',
    'fa-arrow-circle-down': 'ph-arrow-circle-down',
    'fa-money': 'ph-currency-dollar',
    'fa-video-camera': 'ph-video-camera',
    'fa-whatsapp': 'ph-whatsapp-logo',
};

function normalizeIcons(root = document.body) {
    if (!root) return;
    const legacyIcons = root.querySelectorAll('i.fa:not(.ph):not([class*="ph-"]), span.fa:not(.ph):not([class*="ph-"])');
    for (let i = 0; i < legacyIcons.length; i++) {
        const el = legacyIcons[i];
        el.classList.add('ph');
        for (const cls of Array.from(el.classList)) {
            if (FA_TO_PHOSPHOR_MAP[cls]) {
                el.classList.add(FA_TO_PHOSPHOR_MAP[cls]);
            } else if (cls.startsWith('fa-')) {
                const clean = cls.replace(/^fa-/, '').replace(/-o$/, '');
                el.classList.add(`ph-${clean}`);
            }
        }
    }
}

let scheduled = false;
function requestNormalize() {
    if (!scheduled) {
        scheduled = true;
        requestAnimationFrame(() => {
            scheduled = false;
            normalizeIcons(document.body);
        });
    }
}

if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => normalizeIcons(document.body));
    } else {
        normalizeIcons(document.body);
    }

    const observer = new MutationObserver((mutations) => {
        let hasRelevantMutation = false;
        for (let i = 0; i < mutations.length; i++) {
            if (mutations[i].addedNodes.length > 0) {
                hasRelevantMutation = true;
                break;
            }
        }
        if (hasRelevantMutation) {
            requestNormalize();
        }
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
    });
}
