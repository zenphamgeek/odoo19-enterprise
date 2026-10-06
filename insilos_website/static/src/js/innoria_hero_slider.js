/**
 * Innoria Unified Hero Video Slider Engine
 * File: innoria_hero_slider.js
 * Host Target: innoria.insilos.com (Insilos Sovereign Web Platform / Odoo 20)
 *
 * 4 Product Group Themes:
 * 0. DIGIFORCE      - Low-Code Studio, Microservices, OpenAPI
 * 1. MOJO AI        - VLM Computer Vision, 16 Autonomous Agent Swarms
 * 2. MOJOVERSE      - Enterprise Web3, Decentralized DID & Value Mesh
 * 3. INTELLIGENT ERP - SAP-Grade Core (SD, MM, PP, FI/CO), Circular 78
 *
 * Capabilities:
 * - Dual-buffered 60 FPS HTML5 Video Crossfade Engine
 * - Smooth cubic-bezier Opacity & Scale Transitions
 * - requestAnimationFrame Dynamic Progress Bar Filling
 * - High-Contrast Dark Cyber Luxury Ambient Lighting
 * - Playback HUD (Prev, Next, Play/Pause, Mute/Unmute, Counter)
 * - Interactive Feature Chips & Metrics Tile Micro-Interactions
 * - Auto-Pause on Hover for Comfortable Executive Reading
 */

(function () {
    'use strict';

    var THEMES = [
        {
            index: 0,
            name: 'DIGIFORCE',
            accent: '#00F0FF',
            glow: 'rgba(0, 240, 255, 0.4)',
            gradient: 'linear-gradient(135deg, #0ABBDB 0%, #00F0FF 100%)'
        },
        {
            index: 1,
            name: 'MOJO AI',
            accent: '#FF8000',
            glow: 'rgba(255, 128, 0, 0.4)',
            gradient: 'linear-gradient(135deg, #FF8000 0%, #F59E0B 100%)'
        },
        {
            index: 2,
            name: 'MOJOVERSE',
            accent: '#10B981',
            glow: 'rgba(16, 185, 129, 0.4)',
            gradient: 'linear-gradient(135deg, #10B981 0%, #00F5A0 100%)'
        },
        {
            index: 3,
            name: 'INTELLIGENT ERP',
            accent: '#3B82F6',
            glow: 'rgba(59, 130, 246, 0.4)',
            gradient: 'linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)'
        }
    ];

    function InnoriaHeroVideoSlider(container) {
        if (!container || container.__innoria_hero_slider_initialized) return;
        container.__innoria_hero_slider_initialized = true;

        this.container = container;
        this.videoLayers = Array.prototype.slice.call(container.querySelectorAll('.video-slide-layer'));
        this.slideItems = Array.prototype.slice.call(container.querySelectorAll('.hero-slide-item'));
        this.tabBtns = Array.prototype.slice.call(container.querySelectorAll('.hero-product-tab-btn'));
        this.progressFills = Array.prototype.slice.call(container.querySelectorAll('.tab-progress-fill'));
        this.ambientGlow = container.querySelector('#heroAmbientGlow');
        this.hudCounter = container.querySelector('#heroSlideCounter');
        this.prevBtn = container.querySelector('#heroPrevBtn');
        this.nextBtn = container.querySelector('#heroNextBtn');
        this.playPauseBtn = container.querySelector('#heroPlayPauseBtn');
        this.playPauseIcon = container.querySelector('#heroPlayPauseIcon');
        this.muteBtn = container.querySelector('#heroMuteBtn');
        this.muteIcon = container.querySelector('#heroMuteIcon');
        this.contentStage = container.querySelector('.hero-content-stage');

        this.totalSlides = Math.max(this.slideItems.length, this.videoLayers.length, 4);
        this.currentIndex = 0;
        this.slideDuration = 6500; // ms
        this.isPlaying = true;
        this.isMuted = true;
        this.isHoverPaused = false;

        this.startTime = null;
        this.pausedProgress = 0;
        this.rafId = null;

        this._bindEvents();
        this._initVideos();
        this.goToSlide(0, true);
        this._startCycle();
    }

    InnoriaHeroVideoSlider.prototype._initVideos = function () {
        var self = this;
        this.videoLayers.forEach(function (video) {
            video.muted = self.isMuted;
            video.playsInline = true;
            video.loop = true;
            video.preload = 'auto';

            // Ensure video attempts to play smoothly
            var playPromise = video.play();
            if (playPromise !== undefined) {
                playPromise.catch(function () {
                    // Autoplay was prevented by browser policy (safely ignore)
                });
            }
        });
    };

    InnoriaHeroVideoSlider.prototype.goToSlide = function (targetIdx, immediate) {
        var self = this;
        if (targetIdx < 0) targetIdx = this.totalSlides - 1;
        if (targetIdx >= this.totalSlides) targetIdx = 0;

        this.currentIndex = targetIdx;
        var theme = THEMES[targetIdx] || THEMES[0];

        // 1. Crossfade Video Layers
        this.videoLayers.forEach(function (vid, idx) {
            if (idx === targetIdx) {
                vid.classList.add('active');
                if (vid.paused && self.isPlaying) {
                    try {
                        vid.play().catch(function () {});
                    } catch (e) {}
                }
            } else {
                vid.classList.remove('active');
            }
        });

        // 2. Switch Slide Content with Staggered Fade
        this.slideItems.forEach(function (slide, idx) {
            if (idx === targetIdx) {
                slide.classList.add('active');
            } else {
                slide.classList.remove('active');
            }
        });

        // 3. Update Ambient Lighting
        if (this.ambientGlow) {
            this.ambientGlow.style.background = 'radial-gradient(circle, ' + theme.glow + ' 0%, transparent 70%)';
        }

        // 4. Update Navigation Tabs
        this.tabBtns.forEach(function (tab, idx) {
            if (idx === targetIdx) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        // 5. Reset All Progress Bars
        this.progressFills.forEach(function (fill, idx) {
            if (idx === targetIdx) {
                fill.style.width = '0%';
            } else {
                fill.style.width = '0%';
            }
        });

        // 6. Update HUD Counter
        if (this.hudCounter) {
            var currStr = (targetIdx + 1) < 10 ? '0' + (targetIdx + 1) : (targetIdx + 1);
            var totalStr = this.totalSlides < 10 ? '0' + this.totalSlides : this.totalSlides;
            this.hudCounter.textContent = currStr + ' / ' + totalStr;
        }

        // 7. Restart Timer Cycle
        this.pausedProgress = 0;
        this.startTime = performance.now();
    };

    InnoriaHeroVideoSlider.prototype._startCycle = function () {
        var self = this;
        if (this.rafId) cancelAnimationFrame(this.rafId);

        function tick(now) {
            if (!self.startTime) self.startTime = now;

            if (self.isPlaying && !self.isHoverPaused) {
                var elapsed = now - self.startTime + (self.pausedProgress * self.slideDuration);
                var progress = Math.min(elapsed / self.slideDuration, 1.0);

                var activeFill = self.container.querySelector('#tabProgress' + self.currentIndex);
                if (activeFill) {
                    activeFill.style.width = (progress * 100) + '%';
                }

                if (progress >= 1.0) {
                    self.nextSlide();
                    return;
                }
            }

            self.rafId = requestAnimationFrame(tick);
        }

        this.rafId = requestAnimationFrame(tick);
    };

    InnoriaHeroVideoSlider.prototype.nextSlide = function () {
        this.goToSlide((this.currentIndex + 1) % this.totalSlides);
    };

    InnoriaHeroVideoSlider.prototype.prevSlide = function () {
        this.goToSlide((this.currentIndex - 1 + this.totalSlides) % this.totalSlides);
    };

    InnoriaHeroVideoSlider.prototype.togglePlayPause = function () {
        this.isPlaying = !this.isPlaying;

        if (this.isPlaying) {
            this.startTime = performance.now();
            if (this.playPauseIcon) {
                this.playPauseIcon.innerHTML = '<use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-pause"/>';
            }
            if (this.playPauseBtn) this.playPauseBtn.title = 'Tạm dừng';
            var activeVideo = this.videoLayers[this.currentIndex];
            if (activeVideo && activeVideo.paused) {
                activeVideo.play().catch(function () {});
            }
            this._startCycle();
        } else {
            if (this.playPauseIcon) {
                this.playPauseIcon.innerHTML = '<use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-play"/>';
            }
            if (this.playPauseBtn) this.playPauseBtn.title = 'Tiếp tục phát';
            var currVideo = this.videoLayers[this.currentIndex];
            if (currVideo && !currVideo.paused) {
                currVideo.pause();
            }
        }
    };

    InnoriaHeroVideoSlider.prototype.toggleMute = function () {
        this.isMuted = !this.isMuted;
        var self = this;

        this.videoLayers.forEach(function (video) {
            video.muted = self.isMuted;
        });

        if (this.muteIcon) {
            if (this.isMuted) {
                this.muteIcon.innerHTML = '<use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-speaker-slash"/>';
                if (this.muteBtn) this.muteBtn.title = 'Bật âm thanh';
            } else {
                this.muteIcon.innerHTML = '<use href="/insilos_website/static/src/icons/phosphor-duotone.svg#ph-speaker-high"/>';
                if (this.muteBtn) this.muteBtn.title = 'Tắt âm thanh';
            }
        }
    };

    InnoriaHeroVideoSlider.prototype._bindEvents = function () {
        var self = this;

        // Tab Navigation Buttons
        this.tabBtns.forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                var targetIdx = parseInt(btn.getAttribute('data-tab-target'), 10);
                if (!isNaN(targetIdx)) {
                    self.goToSlide(targetIdx);
                }
            });
        });

        // HUD Controls
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', function (e) {
                e.preventDefault();
                self.prevSlide();
            });
        }

        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', function (e) {
                e.preventDefault();
                self.nextSlide();
            });
        }

        if (this.playPauseBtn) {
            this.playPauseBtn.addEventListener('click', function (e) {
                e.preventDefault();
                self.togglePlayPause();
            });
        }

        if (this.muteBtn) {
            this.muteBtn.addEventListener('click', function (e) {
                e.preventDefault();
                self.toggleMute();
            });
        }

        // Reading Pause on Content Hover
        if (this.contentStage) {
            this.contentStage.addEventListener('mouseenter', function () {
                self.isHoverPaused = true;
            });
            this.contentStage.addEventListener('mouseleave', function () {
                self.isHoverPaused = false;
                self.startTime = performance.now();
            });
        }

        // Keyboard Navigation (ArrowLeft / ArrowRight)
        window.addEventListener('keydown', function (e) {
            if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
            if (e.key === 'ArrowRight') {
                self.nextSlide();
            } else if (e.key === 'ArrowLeft') {
                self.prevSlide();
            }
        });
    };

    // Auto-Mount on DOM Ready
    function autoInitHeroSlider() {
        var heroEl = document.querySelector('#innoria_hero_cover, .innoria-hero-slider-section');
        if (heroEl && !heroEl.__innoria_hero_slider_initialized) {
            window.innoriaHeroSlider = new InnoriaHeroVideoSlider(heroEl);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoInitHeroSlider);
    } else {
        autoInitHeroSlider();
    }

    // Expose to window
    if (typeof window !== 'undefined') {
        window.InnoriaHeroVideoSlider = InnoriaHeroVideoSlider;
    }
})();
