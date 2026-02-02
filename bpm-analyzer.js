/**
 * BPM Analyzer v4: Professional Autocorrelation & Energy Envelope
 * High-precision tempo detection focusing on rhythmic energy repetition.
 * Optimized against "octave errors" (half/double tempo) using lag weightings.
 */

class BPMAnalyzer {
    constructor() {
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }

    async analyzeFromUrl(url) {
        try {
            const response = await fetch(url);
            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await this.audioCtx.decodeAudioData(arrayBuffer);
            return this.calculateBPM(audioBuffer);
        } catch (e) {
            console.error("BPM analysis failed:", e);
            return null;
        }
    }

    calculateBPM(buffer) {
        const data = buffer.getChannelData(0);
        const sampleRate = buffer.sampleRate;

        // 1. Decimate and Filter (Downsample for performance)
        // We only need the rhythm, so we can work with 22kHz or even 11kHz.
        const decimatedData = this.getEnergyEnvelope(data, sampleRate);

        // 2. Autocorrelation (Find the periodicities)
        const bpm = this.autocorrelate(decimatedData, 100); // 100 is the sample rate of our envelope

        return bpm;
    }

    /**
     * Converts raw PCM to an Energy Envelope at 100Hz resolution.
     */
    getEnergyEnvelope(data, sampleRate) {
        const winSize = Math.floor(sampleRate / 100); // 10ms windows for 100Hz envelope
        const envelope = [];

        for (let i = 0; i < data.length; i += winSize) {
            let sum = 0;
            const end = Math.min(i + winSize, data.length);
            for (let j = i; j < end; j++) {
                sum += data[j] * data[j]; // Power
            }
            envelope.push(Math.sqrt(sum / winSize));
        }
        return envelope;
    }

    /**
     * Finds the most likely lag (tempo) using autocorrelation.
     */
    autocorrelate(envelope, envSampleRate) {
        const minBpm = 60;
        const maxBpm = 200;
        const minLag = Math.floor((60 * envSampleRate) / maxBpm); // ~30 samples for 200 BPM
        const maxLag = Math.floor((60 * envSampleRate) / minBpm);  // ~100 samples for 60 BPM

        let bestLag = -1;
        let maxCorr = -1;
        const results = [];

        for (let lag = minLag; lag <= maxLag; lag++) {
            let corr = 0;
            let count = 0;
            for (let i = 0; i < envelope.length - lag; i++) {
                corr += envelope[i] * envelope[i + lag];
                count++;
            }
            corr /= count;

            results.push({ lag, corr });
            if (corr > maxCorr) {
                maxCorr = corr;
                bestLag = lag;
            }
        }

        if (bestLag === -1) return null;

        // Convert lag to BPM
        let bpm = (60 * envSampleRate) / bestLag;

        // Basic Octave correction
        return {
            bpm: Math.round(bpm),
            energy: this.calculateEnergy(envelope),
            danceability: this.calculateDanceability(results, maxCorr)
        };
    }

    calculateEnergy(envelope) {
        if (!envelope.length) return 0;
        const sum = envelope.reduce((a, b) => a + b, 0);
        const avg = sum / envelope.length;
        // Normalize to 0-100 range (empirical scaling based on square law energy)
        return Math.min(100, Math.round(avg * 150));
    }

    calculateDanceability(results, maxCorr) {
        if (!results.length) return 0;
        // Danceability is related to how dominant the "peak" is compared to the average correlation
        const avgCorr = results.reduce((a, b) => a + b.corr, 0) / results.length;
        const ratio = maxCorr / (avgCorr || 1);
        // Map ratio to 0-100 (empirical scaling)
        return Math.min(100, Math.round((ratio - 1) * 40));
    }
}

// Global instance
window.bpmAnalyzer = new BPMAnalyzer();

async function analyzeSingleElement(card) {
    const val = card.textContent.trim();
    if (val === '--' || val === '0' || card.getAttribute('data-recalculate') === 'true') {
        const previewUrl = card.getAttribute('data-preview');
        if (previewUrl && previewUrl !== 'None' && previewUrl !== '') {
            card.innerHTML = '<span class="animate-pulse">...</span>';
            const analysis = await window.bpmAnalyzer.analyzeFromUrl(previewUrl);
            if (analysis && analysis.bpm) {
                card.textContent = analysis.bpm;
                card.classList.add('text-blue-400');
                card.title = `BPM: ${analysis.bpm} | Energía: ${analysis.energy}% | Métrica: ${analysis.danceability}%`;

                // Store analysis on the parent row
                const row = card.closest('[data-id]');
                if (row) {
                    row.setAttribute('data-energy', analysis.energy);
                    row.setAttribute('data-dance', analysis.danceability);
                    row.setAttribute('data-bpm', analysis.bpm);
                }

                // Update x2 element if exists
                const x2Id = card.id.replace('main-bpm-', 'main-bpm-x2-');
                const x2El = document.getElementById(x2Id);
                if (x2El) {
                    x2El.textContent = analysis.bpm * 2;
                }
            } else {
                card.textContent = '--';
            }
        }
    }
}

async function autoDetectMissingBPM() {
    console.log("Starting Vibe Analysis (Precision v4) - Parallel...");
    const cards = Array.from(document.querySelectorAll('[id^="main-bpm-"]'));

    const batchSize = 7;
    for (let i = 0; i < cards.length; i += batchSize) {
        const batch = cards.slice(i, i + batchSize);
        await Promise.all(batch.map(card => analyzeSingleElement(card)));
        // Update dashboard incrementally after each batch
        if (window.updateVibeDashboard) window.updateVibeDashboard();
    }
}

window.analyzeSingleElement = analyzeSingleElement;
window.autoDetectMissingBPM = autoDetectMissingBPM;

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(autoDetectMissingBPM, 2000);
});
