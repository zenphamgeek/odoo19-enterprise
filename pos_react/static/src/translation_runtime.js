(() => {
    "use strict";

    const translations = JSON.parse(document.getElementById("pos-react-data").textContent).translations || {};
    window.posReactTranslate = (module, message) => translations[module]?.[message] || message;
})();
