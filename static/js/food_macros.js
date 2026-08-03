const FOOD_MACRO_FACTORS = {
    hydrates: 4,
    proteins: 4,
    fats: 9,
};

function weightToPercent(weightGrams, kcalPer100g, kcalPerGram) {
    if (!kcalPer100g) return null;
    return (weightGrams * kcalPerGram / kcalPer100g) * 100;
}

function percentToWeight(percent, kcalPer100g, kcalPerGram) {
    if (!kcalPer100g) return null;
    return (percent / 100 * kcalPer100g) / kcalPerGram;
}

if (typeof module !== 'undefined') {
    module.exports = { FOOD_MACRO_FACTORS, weightToPercent, percentToWeight };
}

if (typeof document !== 'undefined') {
document.addEventListener('DOMContentLoaded', () => {
    const kcalField = document.getElementById('foodKcalField');
    if (!kcalField) return;

    const macros = {
        hydrates: {
            weight: document.getElementById('foodHydratesWeight'),
            percent: document.getElementById('foodHydratesPercent'),
        },
        proteins: {
            weight: document.getElementById('foodProteinsWeight'),
            percent: document.getElementById('foodProteinsPercent'),
        },
        fats: {
            weight: document.getElementById('foodFatsWeight'),
            percent: document.getElementById('foodFatsPercent'),
        },
    };

    function getKcal() {
        return parseFloat(kcalField.value) || 0;
    }

    function updatePercentFromWeight(macroKey) {
        const { weight, percent } = macros[macroKey];
        const kcal = getKcal();
        const weightValue = parseFloat(weight.value) || 0;
        const result = weightToPercent(weightValue, kcal, FOOD_MACRO_FACTORS[macroKey]);
        percent.value = result === null ? '' : result.toFixed(2);
    }

    function updateWeightFromPercent(macroKey) {
        const { weight, percent } = macros[macroKey];
        const kcal = getKcal();
        const percentValue = parseFloat(percent.value) || 0;
        const result = percentToWeight(percentValue, kcal, FOOD_MACRO_FACTORS[macroKey]);
        if (result === null) return;
        weight.value = result.toFixed(2);
    }

    function recalcAllPercentsFromWeights() {
        Object.keys(macros).forEach(updatePercentFromWeight);
    }

    Object.keys(macros).forEach((macroKey) => {
        const { weight, percent } = macros[macroKey];
        weight.addEventListener('input', () => updatePercentFromWeight(macroKey));
        percent.addEventListener('input', () => updateWeightFromPercent(macroKey));
    });

    kcalField.addEventListener('input', recalcAllPercentsFromWeights);

    recalcAllPercentsFromWeights();
});
}
