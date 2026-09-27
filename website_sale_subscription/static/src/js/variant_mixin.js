import { renderToElement } from "@web/core/utils/render";
import { ProductPage } from '@website_sale/interactions/product_page';
import { patch } from '@web/core/utils/patch';

patch(ProductPage.prototype, {
    _onChangeCombination(ev, parent, combination) {
        if (super._onChangeCombination) {
            super._onChangeCombination(...arguments);
        }
        if (!combination || !combination.is_subscription) {
            return;
        }
        const unit = parent.querySelector(".o_subscription_unit");
        const price = parent.querySelector(".o_subscription_price") || parent.querySelector(".product_price h5");
        const addToCartButton = document.querySelector('#add_to_cart');
        const pricingSelect =
            parent.querySelector(".js_main_product h5:has(.o_subscription_price)") ||
            parent.querySelector(".js_main_product .plan_select");

        if (pricingSelect) {
            const disabledPlanIds = Array.from(
                pricingSelect.querySelectorAll("input[type='radio']:disabled"),
                radioButton => +radioButton.value
            );
            if (disabledPlanIds.length) {
                combination.pricings.forEach(pricing => {
                    if (disabledPlanIds.includes(pricing.plan_id)) pricing.can_be_added = false;
                });
            }
            pricingSelect.replaceWith(
                renderToElement("website_sale_subscription.SubscriptionPricingTableSelect", {
                    combination_info: combination,
                })
            );
        } else {
            const nodeToAppend = parent.querySelector(".js_main_product div div");
            if (nodeToAppend) {
                nodeToAppend.append(
                    renderToElement("website_sale_subscription.SubscriptionPricingTableSelect", {
                        combination_info: combination,
                    })
                );
            }
        }
        if (combination.allow_one_time_sale) {
            parent.querySelector('.product_price')?.classList?.remove('d-inline-block');
        }

        if (addToCartButton) {
            addToCartButton.dataset.subscriptionPlanId = combination.pricings?.length > 0 ? combination.subscription_default_pricing_plan_id : '';
        }
        if (unit) {
            unit.textContent = combination.temporal_unit_display;
        }
        if (price) {
            price.textContent = combination.subscription_default_pricing_price;
        }
    },

    _getOptionalCombinationInfoParam(product) {
        const result = super._getOptionalCombinationInfoParam ? super._getOptionalCombinationInfoParam(...arguments) : {};
        Object.assign(result, {
            'plan_id': product?.querySelector('.product_price .plan_select input[name="plan_id"]:checked')?.value
        });
        return result;
    },
});
