(() => {
    "use strict";

    const entry = window.posReactPlugins
        ?.resolve("paymentAdapter")
        .find(({ id }) => id === "stripe");
    if (!entry) return;

    let terminal;
    let collection;
    let sdkPromise;

    const loadSdk = () => {
        if (window.StripeTerminal) return Promise.resolve(window.StripeTerminal);
        if (sdkPromise) return sdkPromise;
        sdkPromise = new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://js.stripe.com/terminal/v1/";
            script.onload = () => resolve(window.StripeTerminal);
            script.onerror = () => reject(new Error("Stripe Terminal SDK could not load"));
            document.head.append(script);
        });
        return sdkPromise;
    };

    const stripeError = (result, fallback) => {
        if (result?.error) throw new Error(result.error.message || fallback);
        return result;
    };

    const connect = async (context) => {
        const [{ stripe_serial_number: serial }] = await context.rpc(
            "pos.payment.method",
            "read",
            [[context.payment.method.id], ["stripe_serial_number"]]
        );
        if (!serial) throw new Error("No Stripe reader configured");
        if (!terminal) {
            const sdk = await loadSdk();
            terminal = sdk.create({
                onFetchConnectionToken: async () => {
                    const token = await context.rpc("pos.payment.method", "stripe_connection_token", []);
                    return token.secret;
                },
                onUnexpectedReaderDisconnect: () => {},
            });
        }
        if (terminal.getConnectionStatus?.() === "connected") return terminal;
        const discovery = stripeError(
            await terminal.discoverReaders({ simulated: serial === "SIMULATOR" }),
            "Stripe reader discovery failed"
        );
        const reader = discovery.discoveredReaders?.find(
            (candidate) => candidate.serial_number === serial || serial === "SIMULATOR"
        );
        if (!reader) throw new Error("Configured Stripe reader was not found");
        stripeError(await terminal.connectReader(reader, { fail_if_in_use: true }), "Stripe reader connection failed");
        return terminal;
    };

    Object.assign(entry.value, {
        async start(context) {
            const payment = context.payment;
            const stripe = await connect(context);
            const intent = await context.rpc(
                "pos.payment.method",
                "stripe_payment_intent",
                [[payment.method.id], payment.amount]
            );
            collection = stripe.collectPaymentMethod(intent.client_secret, {
                enable_customer_cancellation: true,
            });
            const collected = stripeError(await collection, "Stripe card collection failed");
            collection = null;
            const processed = stripeError(
                await stripe.processPayment(collected.paymentIntent),
                "Stripe payment processing failed"
            );
            const captured = await context.rpc(
                "pos.payment.method",
                "stripe_capture_payment",
                [processed.paymentIntent.id]
            );
            const details = captured.charges?.data?.[0]?.payment_method_details || {};
            const card = details.card_present || details.interac_present || {};
            return {
                state: "done",
                transaction_id: captured.id,
                card_type: details.interac_present ? "interac" : card.brand || false,
            };
        },
        async refund(context) {
            const result = await context.rpc(
                "pos.payment.method",
                "stripe_refund",
                [[context.payment.method.id], context.payment.transaction_id, context.payment.amount]
            );
            if (result?.error) throw new Error(result.error);
            if (!result?.id) throw new Error("Stripe refund failed");
            return { state: "done", transaction_id: result.id };
        },
        async cancel() {
            if (collection && terminal?.cancelCollectPaymentMethod) {
                await terminal.cancelCollectPaymentMethod();
                collection = null;
            }
        },
    });
})();
