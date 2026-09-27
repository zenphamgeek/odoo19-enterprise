/** @insilos-module **/

const value = (bar, key) => Number(bar[key] ?? bar.close);

export function sma(bars, period = 20) {
    return bars.map((bar, index) => {
        if (index + 1 < period) return null;
        const values = bars.slice(index + 1 - period, index + 1).map((item) => value(item, "close"));
        return { time: bar.date || bar.time, value: values.reduce((sum, item) => sum + item, 0) / period };
    }).filter(Boolean);
}

export function ema(bars, period = 20) {
    const multiplier = 2 / (period + 1);
    let previous;
    return bars.map((bar, index) => {
        const close = value(bar, "close");
        previous = index ? close * multiplier + previous * (1 - multiplier) : close;
        return { time: bar.date || bar.time, value: previous };
    });
}

export function rsi(bars, period = 14) {
    let gains = 0, losses = 0;
    return bars.map((bar, index) => {
        if (!index) return null;
        const change = value(bar, "close") - value(bars[index - 1], "close");
        gains = (gains * Math.min(index - 1, period - 1) + Math.max(change, 0)) / Math.min(index, period);
        losses = (losses * Math.min(index - 1, period - 1) + Math.max(-change, 0)) / Math.min(index, period);
        if (index < period) return null;
        return { time: bar.date || bar.time, value: losses ? 100 - 100 / (1 + gains / losses) : 100 };
    }).filter(Boolean);
}

export function atr(bars, period = 14) {
    let previous, current = 0;
    return bars.map((bar, index) => {
        const range = index ? Math.max(value(bar, "high") - value(bar, "low"), Math.abs(value(bar, "high") - previous), Math.abs(value(bar, "low") - previous)) : value(bar, "high") - value(bar, "low");
        previous = value(bar, "close");
        current = index ? (current * Math.min(index - 1, period - 1) + range) / Math.min(index, period) : range;
        return index + 1 < period ? null : { time: bar.date || bar.time, value: current };
    }).filter(Boolean);
}

export function vwap(bars) {
    let totalPriceVolume = 0, totalVolume = 0;
    return bars.map((bar) => {
        const volume = value(bar, "volume") || 0;
        totalPriceVolume += ((value(bar, "high") + value(bar, "low") + value(bar, "close")) / 3) * volume;
        totalVolume += volume;
        return { time: bar.date || bar.time, value: totalVolume ? totalPriceVolume / totalVolume : value(bar, "close") };
    });
}
